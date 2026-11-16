from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_business_session, get_runtime
from app.core.identity import require_identity
from app.modules.matching.schemas import MatchingPage, PolicyView, ScoringPolicy
from app.modules.matching.service import MatchingService
from app.shared.identity import Principal

router = APIRouter(prefix="/matching", tags=["matching"])
Owner = Annotated[Principal, Depends(require_identity)]
Session = Annotated[AsyncSession, Depends(get_business_session)]


@router.get("/capabilities")
async def capabilities(owner: Owner, session: Session, request: Request) -> dict[str, object]:
    async with session.begin():
        return await MatchingService(session, get_runtime(request).settings).capabilities(
            owner.user_id
        )


@router.get("/policies", response_model=list[PolicyView])
async def policies(owner: Owner, session: Session, request: Request) -> list[PolicyView]:
    return await MatchingService(session, get_runtime(request).settings).policies(owner.user_id)


@router.post("/policies", response_model=PolicyView, status_code=201)
async def create_policy(
    body: ScoringPolicy, owner: Owner, session: Session, request: Request
) -> PolicyView:
    async with session.begin():
        return await MatchingService(session, get_runtime(request).settings).create_policy(
            owner.user_id, body
        )


@router.get("/executions/{execution_id}", response_model=MatchingPage)
async def matches(
    execution_id: UUID,
    owner: Owner,
    session: Session,
    request: Request,
    group_id: Annotated[list[UUID] | None, Query(max_length=20)] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> MatchingPage:
    return await MatchingService(session, get_runtime(request).settings).page(
        owner.user_id, execution_id, group_id or [], offset, limit
    )
