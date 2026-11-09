import asyncio
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select, update

from app.core.db import Runtime
from app.core.errors import AppError
from app.main import create_app
from app.modules.auth import AuthService
from app.modules.cv import CvBlob, CvService, CvVault
from app.modules.cv.models import CvAudit, CvStorageIntent, CvVersion
from app.shared.clock import utcnow
from app.shared.document import DocumentInspection, DocumentPage
from tests.document_fixtures import pdf_fixture


async def synthetic_inspector(
    content: bytes, filename: str, content_type: str
) -> DocumentInspection:
    # Isolates filesystem/DB crash tests from parsing. Native parser has its own tests.
    return DocumentInspection(
        status="TEXT", kind="PDF", pages=[DocumentPage(number=1, text="SYNTHETIC_CV_MARKER")]
    )


async def owner(database: Runtime) -> UUID:
    async with database.sessions() as session:
        return (
            await AuthService(session, database.settings).setup_owner(
                "cv@example.test", "fixture-password-for-cv"
            )
        ).id


@pytest.mark.integration
async def test_crash_before_file_recovers_as_failed_and_can_be_deleted(
    database: Runtime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await owner(database)
    settings = database.settings.model_copy(update={"cv_storage_path": tmp_path / "vault"})

    def fail_store(*args: object) -> None:
        raise AppError("SYNTHETIC_STORAGE_FAILURE", "Synthetic unavailable storage", 503)

    monkeypatch.setattr(CvVault, "store", fail_store)
    async with database.sessions() as session:
        with pytest.raises(AppError):
            await CvService(session, settings).upload(
                user, CvBlob("synthetic.pdf", "application/pdf", pdf_fixture()), synthetic_inspector
            )
    async with database.sessions() as session, session.begin():
        await session.execute(
            update(CvStorageIntent).values(created_at=utcnow() - timedelta(minutes=10))
        )
    async with database.sessions() as session:
        assert await CvService(session, settings).recover(user) == 1
    async with database.sessions() as session:
        rows = await CvService(session, settings).list(user)
    assert len(rows) == 1 and rows[0].state == "FAILED"
    async with database.sessions() as session:
        await CvService(session, settings).delete_document(user, rows[0].document_id)
    async with database.sessions() as session:
        assert await CvService(session, settings).list(user) == []


@pytest.mark.integration
async def test_versions_private_payload_owner_scope_and_preserved_original(
    database: Runtime, tmp_path: Path
) -> None:
    user = await owner(database)
    settings = database.settings.model_copy(update={"cv_storage_path": tmp_path / "vault"})
    original = CvBlob("synthetic.pdf", "application/pdf", pdf_fixture())
    async with database.sessions() as session:
        first = await CvService(session, settings).upload(user, original, synthetic_inspector)

    async def append() -> int:
        async with database.sessions() as session:
            version = await CvService(session, settings).upload(
                user,
                CvBlob(
                    "new-synthetic.pdf",
                    "application/pdf",
                    pdf_fixture(text="Different synthetic version"),
                ),
                synthetic_inspector,
                first.document_id,
            )
            return version.number

    assert sorted(await asyncio.gather(append(), append())) == [2, 3]
    async with database.sessions() as session:
        rows = (await session.scalars(select(CvVersion))).all()
        assert all(b"SYNTHETIC_CV_MARKER" not in row.private_payload for row in rows)
        assert all(b"synthetic.pdf" not in row.private_payload for row in rows)
    async with database.sessions() as session:
        assert await CvService(session, settings).download(user, first.id) == original
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await CvService(session, settings).get_version(uuid4(), first.id)
        assert error.value.status == 404
    async with database.sessions() as session:
        assert await CvService(session, settings).list(uuid4()) == []


@pytest.mark.integration
async def test_publication_crash_recovery_and_repeat_are_idempotent(
    database: Runtime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await owner(database)
    settings = database.settings.model_copy(update={"cv_storage_path": tmp_path / "vault"})
    real_store = CvVault.store

    def crash_after_file(self: CvVault, *args: object) -> None:
        # Typed wrapper below binds the original function without changing data.
        real_store(self, *args)  # type: ignore[arg-type]
        raise AppError("SYNTHETIC_CRASH", "Synthetic crash after file publication", 503)

    monkeypatch.setattr(CvVault, "store", crash_after_file)
    async with database.sessions() as session:
        with pytest.raises(AppError, match="Synthetic crash"):
            await CvService(session, settings).upload(
                user, CvBlob("synthetic.pdf", "application/pdf", pdf_fixture()), synthetic_inspector
            )
    monkeypatch.setattr(CvVault, "store", real_store)
    async with database.sessions() as session:
        rows = await CvService(session, settings).list(user)
        assert len(rows) == 1 and rows[0].state == "PUBLISHING"
    async with database.sessions() as session, session.begin():
        await session.execute(
            update(CvStorageIntent).values(created_at=utcnow() - timedelta(minutes=10))
        )
    async with database.sessions() as session:
        assert await CvService(session, settings).recover(user) == 1
    async with database.sessions() as session:
        assert await CvService(session, settings).recover(user) == 0
    async with database.sessions() as session:
        rows = await CvService(session, settings).list(user)
        assert rows[0].state == "READY"
        audits = list(
            (await session.scalars(select(CvAudit).where(CvAudit.action == "UPLOAD"))).all()
        )
        assert len(audits) == 1
    async with database.sessions() as session:
        await CvService(session, settings).delete_document(user, rows[0].document_id)
    assert not await asyncio.to_thread(lambda: list(tmp_path.rglob("*.cv")))
    async with database.sessions() as session:
        assert await CvService(session, settings).list(user) == []


@pytest.mark.integration
async def test_binary_upload_api_auth_limits_download_and_delete(
    database: Runtime, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    await owner(database)
    settings = database.settings.model_copy(update={"cv_storage_path": tmp_path / "vault"})
    app = create_app(settings)
    app.state.cv_inspector = synthetic_inspector
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://localhost:8443",
            headers={"Origin": "https://localhost:8443"},
        ) as client:
            assert (await client.get("/api/cvs")).status_code == 401
            assert (await client.post("/api/cvs", content=b"opaque")).status_code == 401
            assert (
                await client.post(
                    "/api/auth/login",
                    json={
                        "email": "cv@example.test",
                        "password": "fixture-password-for-cv",
                    },
                )
            ).status_code == 200
            headers = {"Content-Type": "application/pdf", "X-CV-Filename": "synthetic.pdf"}
            uploaded = await client.post("/api/cvs", content=pdf_fixture(), headers=headers)
            assert uploaded.status_code == 201
            row = uploaded.json()
            assert row["number"] == 1 and not row["active"]
            version = f"/api/cvs/versions/{row['id']}"
            assert (await client.get(version)).json()["inspection"]["status"] == "TEXT"
            downloaded = await client.get(version + "/download")
            assert downloaded.content == pdf_fixture()
            assert downloaded.headers["content-type"] == "application/octet-stream"
            assert "attachment" in downloaded.headers["content-disposition"]
            assert "sandbox" in downloaded.headers["content-security-policy"]
            too_large = await client.post(
                "/api/cvs", content=b"x" * (5 * 1024 * 1024 + 1), headers=headers
            )
            assert too_large.status_code == 413
            invalid = await client.post(
                "/api/cvs",
                content=b"fixture",
                headers={
                    **headers,
                    "X-CV-Filename": "..%2Fcv.pdf",
                },
            )
            assert invalid.status_code == 422
            assert (await client.delete("/api/cvs/" + row["document_id"])).status_code == 204
            assert (await client.get(version)).status_code == 404
        assert "SYNTHETIC_CV_MARKER" not in caplog.text
    finally:
        await app.state.runtime.engine.dispose()
