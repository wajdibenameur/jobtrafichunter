from uuid import UUID

from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.listings.dedup import DedupPolicy, relation
from app.modules.listings.models import JobListing, ListingProvenance, ListingRelation
from app.modules.listings.search_contracts import (
    ListingFact,
    ListingGroupView,
    ListingLink,
    ListingScan,
)


class ListingCatalog:
    """Public local-search interface. No provider access and no cross-module models."""

    def __init__(self, session: AsyncSession, policy: DedupPolicy | None = None) -> None:
        self.session = session
        self.policy = policy or DedupPolicy()

    async def _reconcile(self, user_id: UUID, key: str) -> tuple[list[list[ListingFact]], bool]:
        rows = list(
            (
                await self.session.scalars(
                    select(JobListing)
                    .join(ListingProvenance, ListingProvenance.listing_id == JobListing.id)
                    .where(
                        ListingProvenance.user_id == user_id, ListingProvenance.identity_key == key
                    )
                    .order_by(JobListing.first_seen_at, JobListing.id)
                    .limit(101)
                )
            ).all()
        )
        facts = [ListingFact.model_validate(row) for row in rows]
        if len(facts) > 100:
            # Never guess a merge when the evidence bucket exceeds its safety bound.
            return [], True
        groups: list[list[ListingFact]] = []
        for fact in facts:
            group = next(
                (
                    g
                    for g in groups
                    if all(relation(fact, member, self.policy) == "DUPLICATE" for member in g)
                ),
                None,
            )
            if group is None:
                groups.append([fact])
            else:
                group.append(fact)
        ids = [fact.id for fact in facts]
        if ids:
            await self.session.execute(
                delete(ListingRelation).where(
                    ListingRelation.user_id == user_id,
                    or_(ListingRelation.left_id.in_(ids), ListingRelation.right_id.in_(ids)),
                )
            )
        for group in groups:
            for fact in group:
                row = await self.session.get(ListingProvenance, fact.id)
                assert row is not None
                row.root_id = group[0].id
        for i, group in enumerate(groups):
            for other in groups[i + 1 :]:
                kind = relation(group[0], other[0], self.policy)
                if kind not in {"CANDIDATE", "REPOST"}:
                    continue
                a, b = group[0], other[0]
                if (
                    kind == "REPOST"
                    and a.published_at
                    and b.published_at
                    and a.published_at > b.published_at
                ):
                    a, b = b, a
                self.session.add(
                    ListingRelation(
                        user_id=user_id,
                        left_id=a.id,
                        right_id=b.id,
                        kind=kind,
                        policy_version=self.policy.version,
                    )
                )
        await self.session.flush()
        return groups, False

    async def scan(self, user_id: UUID, source_ids: list[UUID], limit: int = 500) -> ListingScan:
        if not 1 <= limit <= 500:
            raise ValueError("Local scans are bounded to 500 imports")
        async with self.session.begin():
            # Serialize grouping against imports for the same owner only.
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": user_id.int & ((1 << 63) - 1)}
            )
            selected = list(
                (
                    await self.session.scalars(
                        select(JobListing)
                        .where(
                            JobListing.user_id == user_id,
                            JobListing.source_id.in_(source_ids),
                            JobListing.status != "CLOSED",
                        )
                        .order_by(JobListing.first_seen_at.desc(), JobListing.id)
                        .limit(limit + 1)
                    )
                ).all()
            )
            truncated = len(selected) > limit
            selected = selected[:limit]
            selected_ids = {row.id for row in selected}
            keys = list(
                (
                    await self.session.scalars(
                        select(ListingProvenance.identity_key)
                        .where(
                            ListingProvenance.user_id == user_id,
                            ListingProvenance.listing_id.in_(selected_ids),
                        )
                        .distinct()
                    )
                ).all()
            )
            result: list[ListingGroupView] = []
            for key in sorted(keys):
                groups, overflow = await self._reconcile(user_id, key)
                truncated |= overflow
                if overflow:
                    # Return individually, visibly partial; no false 'new' evidence.
                    bucket_ids = set(
                        (
                            await self.session.scalars(
                                select(ListingProvenance.listing_id).where(
                                    ListingProvenance.user_id == user_id,
                                    ListingProvenance.identity_key == key,
                                    ListingProvenance.listing_id.in_(selected_ids),
                                )
                            )
                        ).all()
                    )
                    groups = [
                        [ListingFact.model_validate(row)]
                        for row in selected
                        if row.id in bucket_ids
                    ]
                for group in groups:
                    members = [fact for fact in group if fact.id in selected_ids]
                    if not members:
                        continue
                    root = group[0]
                    relations = list(
                        (
                            await self.session.scalars(
                                select(ListingRelation).where(
                                    ListingRelation.user_id == user_id,
                                    or_(
                                        ListingRelation.left_id == root.id,
                                        ListingRelation.right_id == root.id,
                                    ),
                                )
                            )
                        ).all()
                    )
                    result.append(
                        ListingGroupView(
                            id=root.id,
                            first_seen_at=min(f.first_seen_at for f in group),
                            members=members,
                            provenance=[
                                ListingLink(
                                    listing_id=f.id,
                                    source_id=f.source_id,
                                    source_name=f.source_name,
                                    original_url=f.original_url,
                                    application_url=f.application_url,
                                )
                                for f in group
                            ],
                            candidate_ids=[
                                r.right_id if r.left_id == root.id else r.left_id
                                for r in relations
                                if r.kind == "CANDIDATE"
                            ],
                            repost_of_id=next(
                                (
                                    r.left_id
                                    for r in relations
                                    if r.kind == "REPOST" and r.right_id == root.id
                                ),
                                None,
                            ),
                            policy_version=self.policy.version,
                            novelty_verified=not overflow,
                        )
                    )
            return ListingScan(
                groups=result,
                scanned=len(selected),
                duplicates=len(selected) - len(result),
                truncated=truncated,
            )
