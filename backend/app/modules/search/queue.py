import asyncio
import random
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Runtime
from app.core.errors import AppError
from app.modules.listings import ListingCatalog, ListingGroupView, ListingScan
from app.modules.search.execution_schemas import ResultView
from app.modules.search.filters import filter_fact
from app.modules.search.models import SearchExecution, SearchResult, SearchTask
from app.modules.search.schemas import SearchCriteria
from app.shared.clock import utcnow


class LeaseLost(Exception):
    pass


@dataclass(frozen=True)
class TaskLease:
    task_id: UUID
    execution_id: UUID
    user_id: UUID
    token: UUID


class SearchQueue:
    def __init__(self, runtime: Runtime, worker_id: str | None = None) -> None:
        self.runtime = runtime
        self.worker_id = worker_id or str(uuid4())

    async def claim(self) -> TaskLease | None:
        now = utcnow()
        async with self.runtime.sessions() as session, session.begin():
            task = (
                await session.scalars(
                    select(SearchTask)
                    .join(SearchExecution)
                    .where(
                        SearchExecution.status.in_(["PENDING", "RUNNING"]),
                        or_(
                            (SearchTask.status == "PENDING") & (SearchTask.next_retry_at <= now),
                            (SearchTask.status == "RUNNING")
                            & (SearchTask.heartbeat_at < now - timedelta(minutes=2)),
                        ),
                    )
                    .order_by(SearchTask.next_retry_at, SearchTask.id)
                    .with_for_update(skip_locked=True, of=SearchTask)
                    .limit(1)
                )
            ).one_or_none()
            if task is None:
                return None
            execution = await session.get(SearchExecution, task.execution_id, with_for_update=True)
            assert execution is not None
            if (
                execution.cancel_requested
                or execution.created_at < now - timedelta(minutes=15)
                or task.attempt >= 3
            ):
                execution.status = (
                    "CANCELLED"
                    if execution.cancel_requested
                    else "TIMED_OUT"
                    if execution.created_at < now - timedelta(minutes=15)
                    else "FAILED"
                )
                execution.reason = (
                    "CANCELLED"
                    if execution.cancel_requested
                    else "EXECUTION_DEADLINE"
                    if execution.status == "TIMED_OUT"
                    else "ATTEMPTS_EXHAUSTED"
                )
                execution.finished_at = now
                task.status = execution.status
                task.lease_token = None
                return None
            task.status, execution.status = "RUNNING", "RUNNING"
            task.attempt += 1
            task.lease_token, task.locked_by, task.heartbeat_at = uuid4(), self.worker_id, now
            execution.started_at = execution.started_at or now
            return TaskLease(task.id, execution.id, execution.user_id, task.lease_token)

    async def heartbeat(self, lease: TaskLease) -> bool:
        async with self.runtime.sessions() as session, session.begin():
            identifier = await session.scalar(
                update(SearchTask)
                .where(
                    SearchTask.id == lease.task_id,
                    SearchTask.lease_token == lease.token,
                    SearchTask.status == "RUNNING",
                    SearchTask.heartbeat_at >= utcnow() - timedelta(minutes=2),
                )
                .values(heartbeat_at=utcnow())
                .returning(SearchTask.id)
            )
            return identifier is not None

    async def _pulse(self, lease: TaskLease) -> None:
        while True:
            await asyncio.sleep(5)
            if not await self.heartbeat(lease):
                return

    async def _load(
        self, lease: TaskLease
    ) -> tuple[SearchCriteria, dict[str, object] | None, int, float]:
        async with self.runtime.sessions() as session:
            task = await session.get(SearchTask, lease.task_id)
            execution = await session.get(SearchExecution, lease.execution_id)
            if task is None or execution is None or task.lease_token != lease.token:
                raise LeaseLost
            return (
                SearchCriteria.model_validate(execution.criteria),
                task.snapshot,
                task.cursor,
                min(180, (execution.created_at + timedelta(minutes=15) - utcnow()).total_seconds()),
            )

    async def _save_snapshot(self, lease: TaskLease, scan: ListingScan) -> None:
        async with self.runtime.sessions() as session, session.begin():
            task, execution = await self._fence(session, lease)
            task.snapshot = scan.model_dump(mode="json")
            task.stage = "FILTER"
            execution.counts = {
                **execution.counts,
                "scanned": scan.scanned,
                "duplicates": scan.duplicates,
            }

    async def _fence(
        self, session: AsyncSession, lease: TaskLease
    ) -> tuple[SearchTask, SearchExecution]:
        task = (
            await session.scalars(
                select(SearchTask).where(SearchTask.id == lease.task_id).with_for_update()
            )
        ).one()
        if (
            task.lease_token != lease.token
            or task.status != "RUNNING"
            or task.heartbeat_at is None
            or task.heartbeat_at < utcnow() - timedelta(minutes=2)
        ):
            raise LeaseLost
        execution = await session.get(SearchExecution, lease.execution_id, with_for_update=True)
        assert execution is not None
        return task, execution

    async def _batch(
        self,
        lease: TaskLease,
        groups: list[ListingGroupView],
        start: int,
        criteria: SearchCriteria,
        truncated: bool,
        final: bool,
    ) -> bool:
        async with self.runtime.sessions() as session, session.begin():
            task, execution = await self._fence(session, lease)
            if execution.cancel_requested:
                self._finish(task, execution, "CANCELLED", "CANCELLED")
                return False
            retained = 0
            for position, group in enumerate(groups, start=start):
                decisions = [
                    (fact, filter_fact(fact, group, criteria, execution.created_at))
                    for fact in group.members
                ]
                accepted = [(fact, decision) for fact, decision in decisions if decision.accepted]
                if not accepted:
                    continue
                fact, decision = min(
                    accepted, key=lambda pair: (len(pair[1].unknown_fields), str(pair[0].id))
                )
                payload = ResultView(
                    group=group, listing=fact, unknown_fields=decision.unknown_fields
                ).model_dump(mode="json")
                inserted = await session.scalar(
                    insert(SearchResult)
                    .values(
                        execution_id=execution.id,
                        group_id=group.id,
                        position=position,
                        payload=payload,
                    )
                    .on_conflict_do_nothing()
                    .returning(SearchResult.group_id)
                )
                retained += inserted is not None
            task.cursor = start + len(groups)
            task.heartbeat_at = utcnow()
            execution.counts = {
                **execution.counts,
                "processed": task.cursor,
                "results": execution.counts.get("results", 0) + retained,
            }
            if final:
                self._finish(
                    task,
                    execution,
                    "PARTIAL" if truncated else "SUCCEEDED",
                    "LOCAL_SCAN_LIMIT" if truncated else None,
                )
            return True

    @staticmethod
    def _finish(
        task: SearchTask, execution: SearchExecution, status: str, reason: str | None
    ) -> None:
        task.status = "SUCCEEDED" if status == "PARTIAL" else status
        task.lease_token = None
        task.locked_by = None
        task.snapshot = None  # Results retain their immutable snapshots; release workset.
        execution.status, execution.reason, execution.finished_at = status, reason, utcnow()

    async def fail(self, lease: TaskLease, code: str, retry: bool = False) -> None:
        async with self.runtime.sessions() as session, session.begin():
            task, execution = await self._fence(session, lease)
            if execution.cancel_requested:
                self._finish(task, execution, "CANCELLED", "CANCELLED")
            elif retry and task.attempt < 3:
                task.status = "PENDING"
                task.lease_token = None
                task.locked_by = None
                task.next_retry_at = utcnow() + timedelta(seconds=2**task.attempt + random.random())
                execution.reason = code
            else:
                self._finish(
                    task, execution, "TIMED_OUT" if code == "TASK_DEADLINE" else "FAILED", code
                )

    async def _process(
        self,
        lease: TaskLease,
        criteria: SearchCriteria,
        snapshot: dict[str, object] | None,
        cursor: int,
    ) -> None:
        if not await self._batch(lease, [], cursor, criteria, False, False):
            return
        if snapshot is None:
            async with self.runtime.sessions() as session:
                scan = await ListingCatalog(session).scan(lease.user_id, criteria.source_ids)
            await self._save_snapshot(lease, scan)
        else:
            scan = ListingScan.model_validate(snapshot)
        groups = sorted(scan.groups, key=lambda group: str(group.id))
        if not groups:
            await self._batch(lease, [], 0, criteria, scan.truncated, True)
        for start in range(cursor, len(groups), 20):
            if not await self._batch(
                lease,
                groups[start : start + 20],
                start,
                criteria,
                scan.truncated,
                start + 20 >= len(groups),
            ):
                break

    async def run_once(self) -> bool:
        # Explicit DB check remains part of --once, even if there is no work.
        async with self.runtime.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        lease = await self.claim()
        if lease is None:
            return False
        pulse = asyncio.create_task(self._pulse(lease))
        try:
            criteria, snapshot, cursor, timeout = await self._load(lease)
            await asyncio.wait_for(
                self._process(lease, criteria, snapshot, cursor), max(0.001, timeout)
            )
        except LeaseLost:
            pass
        except TimeoutError:
            await self._report_failure(lease, "TASK_DEADLINE")
        except DBAPIError as exc:
            transient = (
                exc.connection_invalidated
                or str(getattr(exc.orig, "sqlstate", "")).startswith("08")
                or getattr(exc.orig, "sqlstate", "") in {"40001", "40P01", "53300", "57P01"}
            )
            await self._report_failure(
                lease, "DATABASE_TRANSIENT" if transient else "DATABASE_ERROR", retry=transient
            )
        except AppError as exc:
            await self._report_failure(lease, exc.code)
        except asyncio.CancelledError:
            # Keep durable checkpoint/lease: a later worker recovers after expiry.
            raise
        except Exception:
            await self._report_failure(lease, "PROCESSING_FAILED")
        finally:
            pulse.cancel()
            await asyncio.gather(pulse, return_exceptions=True)
        return True

    async def _report_failure(self, lease: TaskLease, code: str, retry: bool = False) -> None:
        try:
            await self.fail(lease, code, retry)
        except LeaseLost:
            pass  # A replacement worker owns the outcome now.
