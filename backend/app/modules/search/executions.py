import hashlib
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.search.execution_schemas import (
    ExecutionInput,
    ExecutionView,
    ResultsPage,
    ResultView,
    SourceLogView,
)
from app.modules.search.models import (
    CollectionCheckpoint,
    CollectionPlan,
    SearchExecution,
    SearchResult,
    SearchTask,
    SourceExecutionLog,
)
from app.modules.search.schemas import SearchCriteria
from app.modules.search.service import SearchService
from app.modules.sources import CollectionService
from app.shared.clock import utcnow
from app.shared.source_reference import SourceLookup

ACTIVE = {"PENDING", "RUNNING"}


class ExecutionService:
    def __init__(self, session: AsyncSession, collection: CollectionService | None = None) -> None:
        self.session = session
        self.collection = collection

    async def _row(
        self, user_id: UUID, execution_id: UUID, *, lock: bool = False
    ) -> SearchExecution:
        query = select(SearchExecution).where(
            SearchExecution.user_id == user_id, SearchExecution.id == execution_id
        )
        if lock:
            query = query.with_for_update()
        row = (await self.session.scalars(query)).one_or_none()
        if row is None:
            raise AppError("EXECUTION_NOT_FOUND", "Search execution not found", 404)
        return row

    async def _view(self, row: SearchExecution) -> ExecutionView:
        task = (
            await self.session.scalars(select(SearchTask).where(SearchTask.execution_id == row.id))
        ).one()
        logs = (
            await self.session.scalars(
                select(SourceExecutionLog)
                .where(SourceExecutionLog.execution_id == row.id)
                .order_by(SourceExecutionLog.source_name)
            )
        ).all()
        checkpoints = {
            c.source_id: c
            for c in (
                await self.session.scalars(
                    select(CollectionCheckpoint).where(CollectionCheckpoint.execution_id == row.id)
                )
            ).all()
        }
        source_views = []
        for log in logs:
            view = SourceLogView.model_validate(log)
            if cp := checkpoints.get(log.source_id):
                interrupted = row.status not in ACTIVE and cp.state in ACTIVE
                view = view.model_copy(
                    update={
                        "status": row.status if interrupted else cp.state,
                        "reason": (row.reason if interrupted else cp.reason) or "READY",
                        "counts": {
                            "pages": cp.page_index,
                            "collected": cp.collected,
                            "created": cp.created,
                            "existing": cp.existing,
                            "invalid": cp.invalid,
                        },
                    }
                )
            source_views.append(view)
        return ExecutionView(
            id=row.id,
            profile_id=row.profile_id,
            profile_name=row.profile_name,
            scope=row.scope,
            status=row.status,
            criteria=SearchCriteria.model_validate(row.criteria),
            cancel_requested=row.cancel_requested,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            counts=row.counts,
            reason=row.reason,
            stage=task.stage,
            cursor=task.cursor,
            attempt=task.attempt,
            heartbeat_at=task.heartbeat_at,
            sources=source_views,
        )

    async def request(
        self,
        user_id: UUID,
        profile_id: UUID,
        lookup: SourceLookup,
        options: ExecutionInput | None = None,
    ) -> ExecutionView:
        options = options or ExecutionInput(profile_id=profile_id)
        try:
            async with self.session.begin():
                profile = await SearchService(self.session).get(user_id, profile_id)
                criteria = profile.criteria
                if (
                    criteria.mode != "MANUAL"
                    or criteria.linked_cv_id
                    or criteria.min_score
                    or criteria.notifications_enabled
                ):
                    raise AppError(
                        "FEATURE_UNAVAILABLE",
                        "CV search, scoring and notifications are unavailable in this phase",
                        409,
                    )
                if not criteria.source_ids:
                    raise AppError(
                        "SOURCES_REQUIRED", "Choose at least one imported-offer source", 422
                    )
                sources = [await lookup(user_id, identifier) for identifier in criteria.source_ids]
                collection_sources: dict[str, object] = {}
                if options.scope == "COLLECTED_OFFERS":
                    if self.collection is None:
                        raise AppError(
                            "COLLECTION_UNAVAILABLE", "Collection is not configured", 409
                        )
                    for source in sources:
                        available = await self.collection.describe(user_id, source.id)
                        if not available.eligible:
                            raise AppError(
                                available.reason, "Selected source cannot be collected", 409
                            )
                        collection_sources[str(source.id)] = available.limits.model_dump(
                            mode="json"
                        )
                elif any(not source.manual_import_supported for source in sources):
                    raise AppError(
                        "SOURCE_UNAVAILABLE",
                        "Only manual imported-offer sources are available",
                        409,
                    )
                row = SearchExecution(
                    user_id=user_id,
                    profile_id=profile.id,
                    profile_name=profile.name,
                    criteria=criteria.model_dump(mode="json"),
                    scope=options.scope,
                    counts={"scanned": 0, "duplicates": 0, "processed": 0, "results": 0},
                )
                self.session.add(row)
                await self.session.flush()
                self.session.add(
                    SearchTask(
                        execution_id=row.id, stage="COLLECT" if collection_sources else "SCAN"
                    )
                )
                if collection_sources:
                    self.session.add(
                        CollectionPlan(
                            execution_id=row.id,
                            sources=collection_sources,
                            max_results=options.max_results or 10,
                            deadline=utcnow() + timedelta(minutes=15),
                        )
                    )
                    for source in sources:
                        self.session.add(
                            CollectionCheckpoint(
                                execution_id=row.id,
                                source_id=source.id,
                                query_hash=hashlib.sha256(
                                    criteria.model_dump_json().encode()
                                ).hexdigest(),
                            )
                        )
                for source in sources:
                    self.session.add(
                        SourceExecutionLog(
                            execution_id=row.id, source_id=source.id, source_name=source.name
                        )
                    )
                await self.session.flush()
                return await self._view(row)
        except IntegrityError as exc:
            raise AppError(
                "SEARCH_ALREADY_ACTIVE", "A search is already active for this profile", 409
            ) from exc

    async def get(self, user_id: UUID, execution_id: UUID) -> ExecutionView:
        return await self._view(await self._row(user_id, execution_id))

    async def history(self, user_id: UUID, limit: int = 50) -> list[ExecutionView]:
        rows = (
            await self.session.scalars(
                select(SearchExecution)
                .where(SearchExecution.user_id == user_id)
                .order_by(SearchExecution.created_at.desc(), SearchExecution.id)
                .limit(limit)
            )
        ).all()
        return [await self._view(row) for row in rows]

    async def cancel(self, user_id: UUID, execution_id: UUID) -> ExecutionView:
        async with self.session.begin():
            row = await self._row(user_id, execution_id, lock=True)
            if row.status in ACTIVE:
                row.cancel_requested = True
                # Pending execution may already have a leased task: the worker owns
                # task terminalization; cancellation remains a durable request.
                row.reason = "CANCELLATION_REQUESTED"
            await self.session.flush()
            return await self._view(row)

    async def results(
        self,
        user_id: UUID,
        execution_id: UUID,
        limit: int,
        offset: int,
        sort: str = "discovery",
        query: str = "",
    ) -> ResultsPage:
        await self._row(user_id, execution_id)
        # Max 500 persisted results per execution; bounded in-memory sort/filter
        # keeps JSON snapshots immutable and supports explicit null ordering.
        rows = (
            await self.session.scalars(
                select(SearchResult).where(SearchResult.execution_id == execution_id)
            )
        ).all()
        items = [ResultView.model_validate(row.payload) for row in rows]
        if query:
            needle = query.casefold()
            items = [
                item
                for item in items
                if needle
                in " ".join(
                    v or ""
                    for v in (
                        item.listing.title,
                        item.listing.company,
                        item.listing.country,
                        item.listing.city,
                        item.listing.domain,
                    )
                ).casefold()
            ]
        if sort in {"publication", "discovery"}:

            def date_key(item: ResultView) -> tuple[bool, float, str]:
                value = (
                    item.listing.published_at if sort == "publication" else item.group.first_seen_at
                )
                return (value is None, -(value.timestamp() if value else 0), str(item.group.id))

            items.sort(key=date_key)
        elif sort == "visa":
            ranks = {"CONFIRMED": 0, "RELOCATION": 1, "POSSIBLE": 2, "NOT_SPECIFIED": 3, "NONE": 4}
            items.sort(key=lambda item: (ranks[item.listing.visa_status], str(item.group.id)))
        else:
            items.sort(
                key=lambda item: (
                    not bool(getattr(item.listing, sort)),
                    (getattr(item.listing, sort) or "").casefold(),
                    str(item.group.id),
                )
            )
        return ResultsPage(items=items[offset : offset + limit], total=len(items))

    async def count(self, user_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(SearchExecution)
                .where(SearchExecution.user_id == user_id)
            )
            or 0
        )
