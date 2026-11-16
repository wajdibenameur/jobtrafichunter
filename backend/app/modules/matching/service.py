from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.private_payload import PrivatePayload
from app.core.settings import Settings
from app.modules.ai import (
    JobAnalysis,
    JobAnalysisService,
    JobInput,
    TaxonomyService,
    analyze_job,
    content_hash,
)
from app.modules.matching.models import JobMatch, MatchingRun, PolicyRow
from app.modules.matching.schemas import (
    MatchingPage,
    MatchingRunView,
    MatchingSnapshot,
    MatchItem,
    MatchJobInput,
    MatchPreview,
    PolicyView,
    ScoringPolicy,
)
from app.modules.matching.scoring import score_job
from app.modules.profile import ProfileService


@dataclass(frozen=True, repr=False)
class ComputedMatch:
    job: MatchJobInput
    analysis: JobAnalysis
    preview: MatchPreview


class MatchingService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session, self.settings = session, settings
        self.profiles = ProfileService(session, settings)
        self.private = PrivatePayload(
            settings.cv_encryption_key,
            namespace=b"jobhunter/matching/private-db/v1/",
            magic=b"JHMT\x01",
        )

    @staticmethod
    def context(owner: UUID, identifier: UUID, kind: str) -> bytes:
        return f"matching/{owner}/{kind}/{identifier}".encode()

    async def capabilities(self, owner: UUID) -> dict[str, object]:
        try:
            candidate = await self.profiles.for_matching(owner)
        except AppError as exc:
            return {"ready": False, "reason": exc.code, "calibration_status": "UNVALIDATED"}
        return {
            "ready": True,
            "reason": "PREVIEW_ONLY",
            "candidate_id": str(candidate.id),
            "candidate_revision": candidate.revision,
            "calibration_status": "UNVALIDATED",
        }

    async def policies(self, owner: UUID) -> list[PolicyView]:
        rows = (
            await self.session.scalars(
                select(PolicyRow)
                .where(PolicyRow.user_id == owner)
                .order_by(PolicyRow.version.desc())
                .limit(100)
            )
        ).all()
        return [
            PolicyView(id=r.id, version=r.version, policy=ScoringPolicy.model_validate(r.config))
            for r in rows
        ]

    async def create_policy(self, owner: UUID, policy: ScoringPolicy) -> PolicyView:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": owner.int & ((1 << 63) - 1)}
        )
        key = content_hash(policy)
        existing = await self.session.scalar(
            select(PolicyRow).where(PolicyRow.user_id == owner, PolicyRow.config_hash == key)
        )
        if existing is not None:
            return PolicyView(id=existing.id, version=existing.version, policy=policy)
        version = (
            int(
                await self.session.scalar(
                    select(func.max(PolicyRow.version)).where(PolicyRow.user_id == owner)
                )
                or 0
            )
            + 1
        )
        if version > 100:
            raise AppError("POLICY_LIMIT", "At most 100 scoring policies are supported", 409)
        row = PolicyRow(
            user_id=owner, version=version, config_hash=key, config=policy.model_dump(mode="json")
        )
        self.session.add(row)
        await self.session.flush()
        return PolicyView(id=row.id, version=version, policy=policy)

    async def prepare(
        self,
        owner: UUID,
        execution: UUID,
        *,
        policy_id: UUID | None = None,
        source_execution_id: UUID | None = None,
        expected_candidate_id: UUID | None = None,
    ) -> MatchingRunView:
        candidate = await self.profiles.for_matching(owner, expected_candidate_id)
        if policy_id is None:
            policy = await self.create_policy(owner, ScoringPolicy())
        else:
            row = await self.session.scalar(
                select(PolicyRow).where(PolicyRow.user_id == owner, PolicyRow.id == policy_id)
            )
            if row is None:
                raise AppError("POLICY_NOT_FOUND", "Scoring policy not found", 404)
            policy = PolicyView(
                id=row.id, version=row.version, policy=ScoringPolicy.model_validate(row.config)
            )
        snapshot = MatchingSnapshot(
            candidate=candidate,
            taxonomy=await TaxonomyService(self.session).list(),
            policy=policy.policy,
        )
        identifier = uuid4()
        run = MatchingRun(
            id=identifier,
            user_id=owner,
            execution_id=execution,
            source_execution_id=source_execution_id,
            candidate_id=candidate.id,
            cv_version_id=candidate.cv_version_id,
            candidate_revision=candidate.revision,
            policy_version=policy.version,
            policy_id=policy.id,
            private_snapshot=self.private.seal(
                snapshot.model_dump_json().encode(), self.context(owner, identifier, "run")
            ),
        )
        self.session.add(run)
        await self.session.flush()
        return MatchingRunView.model_validate(run)

    async def metadata(self, owner: UUID, execution: UUID) -> MatchingRunView | None:
        row = await self.session.scalar(
            select(MatchingRun).where(
                MatchingRun.user_id == owner, MatchingRun.execution_id == execution
            )
        )
        return MatchingRunView.model_validate(row) if row else None

    async def snapshot(
        self, owner: UUID, execution: UUID
    ) -> tuple[MatchingRunView, MatchingSnapshot]:
        row = await self.session.scalar(
            select(MatchingRun).where(
                MatchingRun.user_id == owner, MatchingRun.execution_id == execution
            )
        )
        if row is None:
            raise AppError("MATCHING_INPUT_UNAVAILABLE", "Matching inputs are unavailable", 409)
        return MatchingRunView.model_validate(row), MatchingSnapshot.model_validate_json(
            self.private.open(row.private_snapshot, self.context(owner, row.id, "run"))
        )

    @staticmethod
    def compute(snapshot: MatchingSnapshot, jobs: list[MatchJobInput]) -> list[ComputedMatch]:
        results = []
        for job in jobs:
            analysis = analyze_job(job, snapshot.taxonomy)
            results.append(ComputedMatch(job, analysis, score_job(snapshot, job, analysis)))
        return results

    def cache_key(self, owner: UUID, snapshot: MatchingSnapshot, job: MatchJobInput) -> str:
        return self.private.digest(
            (
                snapshot.model_dump_json() + job.model_dump_json() + "preview-rules-v1/job-rules-v1"
            ).encode(),
            str(owner).encode(),
        )

    async def score_batch(
        self,
        owner: UUID,
        execution: UUID,
        snapshot: MatchingSnapshot,
        computed: list[ComputedMatch],
        start: int,
        total: int,
    ) -> MatchingRunView:
        # This order matches CV deletion/activation: owner lock before a matching-row lock.
        await self.profiles.for_matching(owner, snapshot.candidate.id)
        run = await self.session.scalar(
            select(MatchingRun)
            .where(MatchingRun.user_id == owner, MatchingRun.execution_id == execution)
            .with_for_update()
        )
        if run is None:
            raise AppError("MATCHING_INPUT_UNAVAILABLE", "Matching inputs were removed", 409)
        if run.cursor > start:
            return MatchingRunView.model_validate(run)
        if run.cursor != start or run.candidate_id != snapshot.candidate.id:
            raise AppError("MATCHING_CHECKPOINT_CONFLICT", "Matching checkpoint changed", 409)
        run.total, run.status = total, "RUNNING"
        for item in computed:
            key = self.cache_key(owner, snapshot, item.job)
            cached = await self.session.scalar(
                select(JobMatch)
                .where(JobMatch.user_id == owner, JobMatch.cache_key == key)
                .order_by(JobMatch.id)
                .limit(1)
            )
            if cached is not None:
                preview = MatchPreview.model_validate_json(
                    self.private.open(
                        cached.private_payload, self.context(owner, cached.id, "match")
                    )
                )
                analysis_id = cached.analysis_id
                run.cache_hits += 1
            else:
                analysis_id, _ = await JobAnalysisService(self.session, self.settings).analyze(
                    owner,
                    JobInput.model_validate(item.job.model_dump()),
                    snapshot.taxonomy,
                    item.analysis,
                )
                preview = item.preview
            identifier = uuid4()
            self.session.add(
                JobMatch(
                    id=identifier,
                    user_id=owner,
                    run_id=run.id,
                    group_id=item.job.group_id,
                    listing_id=item.job.id,
                    analysis_id=analysis_id,
                    cache_key=key,
                    score=preview.score,
                    private_payload=self.private.seal(
                        preview.model_dump_json().encode(), self.context(owner, identifier, "match")
                    ),
                )
            )
        run.cursor = start + len(computed)
        await self.session.flush()
        return MatchingRunView.model_validate(run)

    async def finish(self, owner: UUID, execution: UUID, status: str) -> None:
        row = await self.session.scalar(
            select(MatchingRun)
            .where(MatchingRun.user_id == owner, MatchingRun.execution_id == execution)
            .with_for_update()
        )
        if row is not None:
            row.status = status

    async def page(
        self, owner: UUID, execution: UUID, group_ids: list[UUID], offset: int, limit: int
    ) -> MatchingPage:
        run = await self.metadata(owner, execution)
        if run is None:
            raise AppError("MATCHING_NOT_FOUND", "Matching preview not found", 404)
        query = select(JobMatch).where(JobMatch.user_id == owner, JobMatch.run_id == run.id)
        if group_ids:
            query = query.where(JobMatch.group_id.in_(group_ids))
        rows = (
            await self.session.scalars(
                query.order_by(JobMatch.group_id).offset(offset).limit(limit)
            )
        ).all()
        items = [
            MatchItem(
                group_id=row.group_id,
                listing_id=row.listing_id,
                preview=MatchPreview.model_validate_json(
                    self.private.open(row.private_payload, self.context(owner, row.id, "match"))
                ),
            )
            for row in rows
        ]
        return MatchingPage(run=run, items=items)


async def matching_metadata(
    session: AsyncSession, owner: UUID, execution: UUID
) -> MatchingRunView | None:
    row = await session.scalar(
        select(MatchingRun).where(
            MatchingRun.user_id == owner, MatchingRun.execution_id == execution
        )
    )
    return MatchingRunView.model_validate(row) if row else None
