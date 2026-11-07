import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_business_session, get_runtime
from app.core.identity import require_identity
from app.modules.listings import ListingService
from app.modules.search.execution_schemas import (
    DashboardView,
    ExecutionInput,
    ExecutionView,
    ResultsPage,
)
from app.modules.search.executions import ACTIVE, ExecutionService
from app.modules.search.schemas import DuplicateInput, ProfileInput, ProfileView
from app.modules.search.service import SearchService
from app.shared.identity import Principal
from app.shared.source_reference import SourceLookup

router = APIRouter(prefix="/search", tags=["search"])
Owner = Annotated[Principal, Depends(require_identity)]
Session = Annotated[AsyncSession, Depends(get_business_session)]


async def validate_sources(body: ProfileInput, request: Request, user_id: UUID) -> None:
    for source_id in body.criteria.source_ids:
        await cast(SourceLookup, request.app.state.source_lookup)(user_id, source_id)


@router.get("/profiles", response_model=list[ProfileView])
async def profiles(owner: Owner, session: Session) -> list[ProfileView]:
    return await SearchService(session).profiles(owner.user_id)


@router.post("/profiles", response_model=ProfileView, status_code=201)
async def create(
    body: ProfileInput, request: Request, owner: Owner, session: Session
) -> ProfileView:
    await validate_sources(body, request, owner.user_id)
    return await SearchService(session).create(owner.user_id, body)


@router.post("/profiles/examples", response_model=list[ProfileView])
async def examples(owner: Owner, session: Session) -> list[ProfileView]:
    return await SearchService(session).examples(owner.user_id)


@router.get("/profiles/{profile_id}", response_model=ProfileView)
async def profile(profile_id: UUID, owner: Owner, session: Session) -> ProfileView:
    return await SearchService(session).get(owner.user_id, profile_id)


@router.put("/profiles/{profile_id}", response_model=ProfileView)
async def update(
    profile_id: UUID, body: ProfileInput, request: Request, owner: Owner, session: Session
) -> ProfileView:
    await validate_sources(body, request, owner.user_id)
    return await SearchService(session).update(owner.user_id, profile_id, body)


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete(profile_id: UUID, owner: Owner, session: Session) -> Response:
    await SearchService(session).delete(owner.user_id, profile_id)
    return Response(status_code=204)


@router.post("/profiles/{profile_id}/duplicate", response_model=ProfileView, status_code=201)
async def duplicate(
    profile_id: UUID, body: DuplicateInput, owner: Owner, session: Session
) -> ProfileView:
    return await SearchService(session).duplicate(owner.user_id, profile_id, body.name)


@router.post("/executions", response_model=ExecutionView, status_code=202)
async def start_execution(
    body: ExecutionInput, request: Request, owner: Owner, session: Session
) -> ExecutionView:
    return await ExecutionService(session).request(
        owner.user_id, body.profile_id, cast(SourceLookup, request.app.state.source_lookup)
    )


@router.get("/executions", response_model=list[ExecutionView])
async def executions(
    owner: Owner, session: Session, limit: int = Query(default=50, ge=1, le=100)
) -> list[ExecutionView]:
    return await ExecutionService(session).history(owner.user_id, limit)


@router.get("/executions/{execution_id}", response_model=ExecutionView)
async def execution(execution_id: UUID, owner: Owner, session: Session) -> ExecutionView:
    return await ExecutionService(session).get(owner.user_id, execution_id)


@router.post("/executions/{execution_id}/cancel", response_model=ExecutionView)
async def cancel(execution_id: UUID, owner: Owner, session: Session) -> ExecutionView:
    return await ExecutionService(session).cancel(owner.user_id, execution_id)


@router.get("/executions/{execution_id}/results", response_model=ResultsPage)
async def results(
    execution_id: UUID,
    owner: Owner,
    session: Session,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Literal["discovery", "publication", "country", "domain", "visa"] = "discovery",
    q: str = Query(default="", max_length=200),
) -> ResultsPage:
    return await ExecutionService(session).results(
        owner.user_id, execution_id, limit, offset, sort, q
    )


@router.get("/executions/{execution_id}/events")
async def events(execution_id: UUID, request: Request, owner: Owner) -> StreamingResponse:
    runtime = get_runtime(request)
    async with runtime.sessions() as session:
        await ExecutionService(session).get(owner.user_id, execution_id)

    async def stream() -> AsyncIterator[str]:
        previous = ""
        for _ in range(20):
            if await request.is_disconnected():
                break
            async with runtime.sessions() as session:
                view = await ExecutionService(session).get(owner.user_id, execution_id)
            encoded = view.model_dump_json()
            if encoded != previous:
                yield f"event: progress\ndata: {encoded}\n\n"
                previous = encoded
            else:
                yield ": keepalive\n\n"
            if view.status not in ACTIVE:
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/dashboard", response_model=DashboardView)
async def dashboard(owner: Owner, session: Session) -> DashboardView:
    page = await ListingService(session).page(owner.user_id, 1, 0)
    history = await ExecutionService(session).history(owner.user_id, 1)
    return DashboardView(imported_count=page.total, last_execution=history[0] if history else None)
