from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_business_session
from app.core.identity import require_identity
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
