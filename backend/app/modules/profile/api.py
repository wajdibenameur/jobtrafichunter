from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_business_session, get_runtime
from app.core.identity import require_identity
from app.modules.ai import SkillDefinition, TaxonomyService
from app.modules.cv import CvService
from app.modules.profile.schemas import CandidateInput, CandidateView, GenerateInput, ValidateInput
from app.modules.profile.service import ProfileService
from app.shared.identity import Principal

router = APIRouter(prefix="/candidate-profiles", tags=["candidate profiles"])
Owner = Annotated[Principal, Depends(require_identity)]
Session = Annotated[AsyncSession, Depends(get_business_session)]


@router.get("/taxonomy", response_model=list[SkillDefinition])
async def taxonomy(owner: Owner, session: Session) -> list[SkillDefinition]:
    return await TaxonomyService(session).list()


@router.put("/taxonomy", response_model=SkillDefinition)
async def set_term(
    body: SkillDefinition, owner: Owner, session: Session, request: Request
) -> SkillDefinition:
    async with session.begin():
        await CvService(session, get_runtime(request).settings).lock_owner(owner.user_id)
        return await TaxonomyService(session).set(body)


@router.get("/active", response_model=CandidateView)
async def active(owner: Owner, session: Session, request: Request) -> CandidateView:
    return await ProfileService(session, get_runtime(request).settings).validated_active(
        owner.user_id
    )


@router.get("/versions/{cv_version}/export")
async def export(cv_version: UUID, owner: Owner, session: Session, request: Request) -> Response:
    import json

    async with session.begin():
        data = await CvService(session, get_runtime(request).settings).export_version(
            owner.user_id, cv_version
        )
        profiles = await ProfileService(session, get_runtime(request).settings).list(
            owner.user_id, cv_version
        )
        data["candidate_profiles"] = [p.model_dump(mode="json") for p in profiles]
    return Response(
        json.dumps(data, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="cv-export-{cv_version}.json"',
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.get("/versions/{cv_version}", response_model=list[CandidateView])
async def history(
    cv_version: UUID, owner: Owner, session: Session, request: Request
) -> list[CandidateView]:
    return await ProfileService(session, get_runtime(request).settings).list(
        owner.user_id, cv_version
    )


@router.post("/versions/{cv_version}/generate", response_model=CandidateView)
async def generate(
    cv_version: UUID, body: GenerateInput, owner: Owner, session: Session, request: Request
) -> CandidateView:
    return await ProfileService(session, get_runtime(request).settings).generate(
        owner.user_id, cv_version, body.regenerate
    )


@router.get("/{profile_id}", response_model=CandidateView)
async def get(profile_id: UUID, owner: Owner, session: Session, request: Request) -> CandidateView:
    return await ProfileService(session, get_runtime(request).settings).get(
        owner.user_id, profile_id
    )


@router.post("/{profile_id}/revisions", response_model=CandidateView, status_code=201)
async def edit(
    profile_id: UUID, body: CandidateInput, owner: Owner, session: Session, request: Request
) -> CandidateView:
    return await ProfileService(session, get_runtime(request).settings).edit(
        owner.user_id, profile_id, body
    )


@router.post("/{profile_id}/validate", response_model=CandidateView)
async def validate(
    profile_id: UUID, body: ValidateInput, owner: Owner, session: Session, request: Request
) -> CandidateView:
    return await ProfileService(session, get_runtime(request).settings).validate(
        owner.user_id, profile_id
    )


@router.post("/{profile_id}/activate", response_model=CandidateView)
async def activate(
    profile_id: UUID, owner: Owner, session: Session, request: Request
) -> CandidateView:
    return await ProfileService(session, get_runtime(request).settings).activate(
        owner.user_id, profile_id
    )
