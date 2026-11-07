from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_business_session
from app.core.identity import require_identity
from app.modules.sources.schemas import (
    SearchLinkRequest,
    SearchLinkView,
    SourceCreate,
    SourcePatch,
    SourceView,
)
from app.modules.sources.service import SourceService
from app.shared.identity import Principal

router = APIRouter(prefix="/sources", tags=["sources"])
Owner = Annotated[Principal, Depends(require_identity)]
Session = Annotated[AsyncSession, Depends(get_business_session)]


@router.get("", response_model=list[SourceView])
async def sources(owner: Owner, session: Session) -> list[SourceView]:
    return await SourceService(session).list(owner.user_id)


@router.post("", response_model=SourceView, status_code=201)
async def create(body: SourceCreate, owner: Owner, session: Session) -> SourceView:
    return await SourceService(session).create(owner.user_id, body)


@router.patch("/{source_id}", response_model=SourceView)
async def update(source_id: UUID, body: SourcePatch, owner: Owner, session: Session) -> SourceView:
    return await SourceService(session).patch(owner.user_id, source_id, body)


@router.delete("/{source_id}", status_code=204)
async def delete(source_id: UUID, owner: Owner, session: Session) -> Response:
    await SourceService(session).delete(owner.user_id, source_id)
    return Response(status_code=204)


@router.post("/{source_id}/search-link", response_model=SearchLinkView)
async def search_link(
    source_id: UUID, body: SearchLinkRequest, owner: Owner, session: Session
) -> SearchLinkView:
    return await SourceService(session).search_link(owner.user_id, source_id, body)
