from collections.abc import Awaitable, Callable
from typing import Annotated, Literal, cast
from urllib.parse import quote, unquote
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_business_session, get_runtime
from app.core.errors import AppError
from app.core.identity import require_identity
from app.modules.cv.schemas import CvVersionData, CvVersionView
from app.modules.cv.service import CvService
from app.modules.cv.vault import CvBlob
from app.shared.document import DocumentInspector
from app.shared.identity import Principal

router = APIRouter(prefix="/cvs", tags=["cvs"])
Owner = Annotated[Principal, Depends(require_identity)]
Session = Annotated[AsyncSession, Depends(get_business_session)]
Filename = Annotated[str, Header(alias="X-CV-Filename", min_length=1, max_length=2400)]
MediaType = Literal[
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
]


@router.get("/capabilities")
async def capabilities(request: Request, owner: Owner) -> dict[str, object]:
    try:
        await cast(Callable[[], Awaitable[None]], request.app.state.cv_probe)()
    except (AppError, ValueError, OSError):
        ready = False
    else:
        ready = True
    return {
        "ready": ready,
        "formats": ["PDF", "DOCX"],
        "doc": False,
        "ocr": False,
        "max_bytes": 5 * 1024 * 1024,
    }


@router.get("", response_model=list[CvVersionView])
async def versions(request: Request, owner: Owner, session: Session) -> list[CvVersionView]:
    return await CvService(session, get_runtime(request).settings).list(owner.user_id)


async def store_upload(
    request: Request,
    name: str,
    owner: Principal,
    session: AsyncSession,
    document_id: UUID | None,
) -> CvVersionView:
    try:
        filename = unquote(name, encoding="utf-8", errors="strict")
    except UnicodeError:
        raise AppError("CV_FILENAME_INVALID", "Invalid CV filename", 422) from None
    blob = CvBlob(
        filename,
        cast(MediaType, request.headers.get("content-type", "").split(";")[0]),
        await request.body(),
    )
    return await CvService(session, get_runtime(request).settings).upload(
        owner.user_id, blob, cast(DocumentInspector, request.app.state.cv_inspector), document_id
    )


@router.post("", response_model=CvVersionView, status_code=201)
async def upload(request: Request, owner: Owner, session: Session, name: Filename) -> CvVersionView:
    return await store_upload(request, name, owner, session, None)


@router.post("/{document_id}/versions", response_model=CvVersionView, status_code=201)
async def replace(
    document_id: UUID, request: Request, owner: Owner, session: Session, name: Filename
) -> CvVersionView:
    return await store_upload(request, name, owner, session, document_id)


@router.get("/versions/{version_id}", response_model=CvVersionData)
async def inspect(
    version_id: UUID, request: Request, owner: Owner, session: Session
) -> CvVersionData:
    return await CvService(session, get_runtime(request).settings).get_version(
        owner.user_id, version_id
    )


@router.get("/versions/{version_id}/download")
async def download(version_id: UUID, request: Request, owner: Owner, session: Session) -> Response:
    blob = await CvService(session, get_runtime(request).settings).download(
        owner.user_id, version_id
    )
    return Response(
        blob.content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=\"cv-original\"; filename*=UTF-8''"
            + quote(blob.filename),
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID, request: Request, owner: Owner, session: Session
) -> Response:
    await CvService(session, get_runtime(request).settings).delete_document(
        owner.user_id, document_id
    )
    return Response(status_code=204)
