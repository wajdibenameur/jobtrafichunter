from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_business_session
from app.core.errors import AppError
from app.core.identity import require_identity
from app.modules.listings.csv_import import preview_csv
from app.modules.listings.schemas import (
    CsvPreview,
    CsvPreviewRequest,
    ImportRequest,
    ImportResult,
    ListingsPage,
)
from app.modules.listings.service import ListingService
from app.shared.identity import Principal
from app.shared.source_reference import SourceLookup

router = APIRouter(prefix="/jobs", tags=["manual import"])
Owner = Annotated[Principal, Depends(require_identity)]
Session = Annotated[AsyncSession, Depends(get_business_session)]


@router.post("/import/preview", response_model=CsvPreview)
async def preview(body: CsvPreviewRequest, request: Request, owner: Owner) -> CsvPreview:
    source = await cast(SourceLookup, request.app.state.source_lookup)(
        owner.user_id, body.source_id
    )
    if not source.manual_import_supported:
        raise AppError("IMPORT_NOT_SUPPORTED", "Manual import unavailable", 409)
    return preview_csv(body.csv_text)


@router.post("/import", response_model=ImportResult, status_code=201)
async def import_jobs(
    body: ImportRequest, request: Request, owner: Owner, session: Session
) -> ImportResult:
    source = await cast(SourceLookup, request.app.state.source_lookup)(
        owner.user_id, body.source_id
    )
    return await ListingService(session).import_jobs(owner.user_id, source, body)


@router.get("", response_model=ListingsPage)
async def jobs(
    owner: Owner,
    session: Session,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListingsPage:
    return await ListingService(session).page(owner.user_id, limit, offset)
