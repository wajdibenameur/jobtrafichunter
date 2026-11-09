from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.db import Runtime
from app.core.errors import AppError
from app.modules.ai import SkillDefinition
from app.modules.auth import AuthService
from app.modules.cv import CvBlob, CvService
from app.modules.profile import ProfileService
from app.modules.profile.extraction import propose_profile
from app.modules.profile.models import CandidateProfileVersion
from app.modules.profile.schemas import CandidateFields, CandidateInput
from app.shared.document import DocumentInspection, DocumentPage
from tests.document_fixtures import pdf_fixture


def test_evidenced_mentions_and_sections_never_guess_missing_facts() -> None:
    text = (
        "Synthetic Person\nProfessional title: Developer\n"
        "Education\nSynthetic degree\nExperience\nSynthetic company 2021-2023\n"
        "Skills\nPython K8s\nLanguages\nFrench\n"
    )
    document = DocumentInspection(
        status="TEXT", kind="PDF", pages=[DocumentPage(number=1, text=text)]
    )
    data = propose_profile(
        document,
        [
            SkillDefinition(canonical="Python", category="languages"),
            SkillDefinition(canonical="Kubernetes", category="devops", aliases=["K8s"]),
        ],
    )
    assert data.fields.professional_title == "Developer"
    assert data.fields.skills["devops"] == ["Kubernetes"]
    assert data.fields.education == ["Synthetic degree"]
    assert data.fields.experiences == ["Synthetic company 2021-2023"]
    assert data.fields.years_experience is None and data.preferences.visa_needed is None
    for proofs in data.evidence.values():
        for proof in proofs:
            assert text[proof.start : proof.end] == proof.quote
    empty = propose_profile(
        DocumentInspection(status="NEEDS_OCR", kind="PDF", pages=[DocumentPage(number=1, text="")]),
        [],
    )
    assert empty.fields.professional_title is None and empty.fields.skills == {}
    assert "OCR_UNAVAILABLE" in empty.warnings


@pytest.mark.integration
async def test_candidate_versions_validation_activation_scope_and_delete_cascade(
    database: Runtime, tmp_path: Path
) -> None:
    async with database.sessions() as session:
        user = (
            await AuthService(session, database.settings).setup_owner(
                "profile@example.test", "fixture-password-for-profile"
            )
        ).id
    settings = database.settings.model_copy(update={"cv_storage_path": tmp_path / "vault"})

    async def inspect(content: bytes, filename: str, content_type: str) -> DocumentInspection:
        return DocumentInspection(
            status="TEXT",
            kind="PDF",
            pages=[DocumentPage(number=1, text="SYNTHETIC_CV_MARKER Python Angular")],
        )

    async with database.sessions() as session:
        cv = await CvService(session, settings).upload(
            user, CvBlob("synthetic.pdf", "application/pdf", pdf_fixture()), inspect
        )
    async with database.sessions() as session:
        first = await ProfileService(session, settings).generate(user, cv.id, False)
    assert first.status == "DRAFT" and not first.active
    assert first.data.fields.skills["languages"] == ["Python"]
    assert first.data.fields.professional_title is None
    async with database.sessions() as session:
        assert (await ProfileService(session, settings).generate(user, cv.id, False)).id == first.id
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await ProfileService(session, settings).activate(user, first.id)
        assert error.value.code == "CANDIDATE_NOT_VALIDATED"
    body = CandidateInput(
        fields=first.data.fields.model_copy(update={"professional_title": "Developer"})
    )
    async with database.sessions() as session:
        edited = await ProfileService(session, settings).edit(user, first.id, body)
    assert edited.parent_id == first.id and edited.revision == 2
    assert edited.data.origins["professional_title"] == "USER_EDITED"
    async with database.sessions() as session:
        validated = await ProfileService(session, settings).validate(user, edited.id)
    assert validated.status == "VALIDATED" and not validated.active
    async with database.sessions() as session:
        assert (await ProfileService(session, settings).activate(user, edited.id)).active
    async with database.sessions() as session:
        another = await ProfileService(session, settings).edit(
            user,
            edited.id,
            CandidateInput(fields=CandidateFields(professional_title="Changed only in draft")),
        )
    assert not another.active and another.status == "DRAFT"
    async with database.sessions() as session:
        assert (await ProfileService(session, settings).validated_active(user)).id == edited.id
        rows = (await session.scalars(select(CandidateProfileVersion))).all()
        assert all(b"SYNTHETIC_CV_MARKER" not in row.private_payload for row in rows)
    async with database.sessions() as session:
        with pytest.raises(AppError) as foreign:
            await ProfileService(session, settings).get(uuid4(), edited.id)
        assert foreign.value.status == 404
    async with database.sessions() as session:
        await CvService(session, settings).delete_document(user, cv.document_id)
    async with database.sessions() as session:
        with pytest.raises(AppError) as removed:
            await ProfileService(session, settings).validated_active(user)
        assert removed.value.code == "CANDIDATE_NOT_ACTIVE"
        assert not list((await session.scalars(select(CandidateProfileVersion))).all())
