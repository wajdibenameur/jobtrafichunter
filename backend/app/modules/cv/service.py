import asyncio
import base64
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.settings import Settings
from app.modules.cv.models import ActiveCv, CvAudit, CvDocument, CvStorageIntent, CvVersion
from app.modules.cv.private_data import PrivateCvData
from app.modules.cv.schemas import CvPrivatePayload, CvVersionData, CvVersionView
from app.modules.cv.vault import CvBlob, CvVault, VaultIdentity
from app.shared.clock import utcnow
from app.shared.document import DocumentInspector


class CvService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.vault = CvVault(settings.cv_storage_path, settings.cv_encryption_key)
        self.private = PrivateCvData(settings.cv_encryption_key)

    @staticmethod
    def _context(user_id: UUID, version_id: UUID) -> bytes:
        return f"inspection/{user_id}/{version_id}".encode()

    async def lock_owner(self, user_id: UUID) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": user_id.int & ((1 << 63) - 1)}
        )

    async def _row(self, user_id: UUID, version_id: UUID) -> CvVersion:
        row = await self.session.scalar(
            select(CvVersion).where(
                CvVersion.id == version_id, CvVersion.user_id == user_id, CvVersion.state == "READY"
            )
        )
        if row is None:
            raise AppError("CV_NOT_FOUND", "CV version not found", 404)
        return row

    def _payload(self, row: CvVersion) -> CvPrivatePayload:
        return CvPrivatePayload.model_validate_json(
            self.private.open(row.private_payload, self._context(row.user_id, row.id))
        )

    async def _view(self, row: CvVersion) -> CvVersionView:
        payload = self._payload(row)
        active = await self.session.get(ActiveCv, row.user_id)
        return CvVersionView(
            id=row.id,
            document_id=row.document_id,
            number=row.number,
            filename=payload.filename,
            byte_size=row.byte_size,
            state=row.state,
            analysis_status=payload.inspection.status,
            active=active is not None and active.version_id == row.id,
            created_at=row.created_at,
        )

    async def list(self, user_id: UUID) -> list[CvVersionView]:
        rows = (
            await self.session.scalars(
                select(CvVersion)
                .where(CvVersion.user_id == user_id, CvVersion.state != "DELETING")
                .order_by(CvVersion.created_at.desc(), CvVersion.id)
                .limit(200)
            )
        ).all()
        return [await self._view(row) for row in rows]

    async def get_version(self, user_id: UUID, version_id: UUID) -> CvVersionData:
        row = await self._row(user_id, version_id)
        return CvVersionData(
            version=await self._view(row), inspection=self._payload(row).inspection
        )

    async def upload(
        self,
        user_id: UUID,
        blob: CvBlob,
        inspector: DocumentInspector,
        document_id: UUID | None = None,
    ) -> CvVersionView:
        inspection = await inspector(blob.content, blob.filename, blob.content_type)
        version_id = uuid4()
        async with self.session.begin():
            await self.lock_owner(user_id)
            count = await self.session.scalar(
                select(func.count()).select_from(CvVersion).where(CvVersion.user_id == user_id)
            )
            if count is not None and count >= 200:
                raise AppError("CV_LIMIT", "At most 200 CV versions are supported", 409)
            if document_id is None:
                document_id = uuid4()
                self.session.add(CvDocument(id=document_id, user_id=user_id))
                await self.session.flush()
            else:
                document = await self.session.scalar(
                    select(CvDocument).where(
                        CvDocument.id == document_id,
                        CvDocument.user_id == user_id,
                        CvDocument.state == "READY",
                    )
                )
                if document is None:
                    raise AppError("CV_NOT_FOUND", "CV document not found", 404)
            number = (
                int(
                    await self.session.scalar(
                        select(func.max(CvVersion.number)).where(
                            CvVersion.document_id == document_id
                        )
                    )
                    or 0
                )
                + 1
            )
            payload = CvPrivatePayload(
                filename=blob.filename, content_type=blob.content_type, inspection=inspection
            )
            row = CvVersion(
                id=version_id,
                user_id=user_id,
                document_id=document_id,
                number=number,
                byte_size=len(blob.content),
                private_payload=self.private.seal(
                    payload.model_dump_json().encode(), self._context(user_id, version_id)
                ),
            )
            self.session.add(row)
            self.session.add(
                CvStorageIntent(
                    user_id=user_id, document_id=document_id, version_id=version_id, kind="PUBLISH"
                )
            )
        # Intent committed before the first filesystem mutation. Cancellation or
        # a crash leaves a discoverable intent; never erase an existing original.
        await asyncio.to_thread(
            self.vault.store, VaultIdentity(user_id, document_id, version_id), blob
        )
        async with self.session.begin():
            await self.lock_owner(user_id)
            return await self._publish(user_id, version_id)

    async def _publish(self, user_id: UUID, version_id: UUID) -> CvVersionView:
        row = await self.session.get(CvVersion, version_id, populate_existing=True)
        if row is None or row.user_id != user_id or row.state != "PUBLISHING":
            raise AppError("CV_STORAGE_CONFLICT", "CV publication state changed", 409)
        document = await self.session.get(CvDocument, row.document_id)
        if document is None or document.state != "READY":
            raise AppError("CV_STORAGE_CONFLICT", "CV document is being deleted", 409)
        intent = await self.session.scalar(
            select(CvStorageIntent).where(
                CvStorageIntent.version_id == version_id, CvStorageIntent.kind == "PUBLISH"
            )
        )
        assert intent is not None
        row.state, intent.done = "READY", True
        self.session.add(
            CvAudit(
                user_id=user_id, document_id=row.document_id, version_id=row.id, action="UPLOAD"
            )
        )
        await self.session.flush()
        return await self._view(row)

    async def download(self, user_id: UUID, version_id: UUID) -> CvBlob:
        async with self.session.begin():
            await self.lock_owner(user_id)
            row = await self._row(user_id, version_id)
            blob = await asyncio.to_thread(
                self.vault.read, VaultIdentity(user_id, row.document_id, row.id)
            )
            self.session.add(
                CvAudit(
                    user_id=user_id,
                    document_id=row.document_id,
                    version_id=row.id,
                    action="DOWNLOAD",
                )
            )
            return blob

    async def activate_validated(self, user_id: UUID, version_id: UUID) -> None:
        """Called by profile inside its validation/activation transaction only."""
        row = await self._row(user_id, version_id)
        await self.session.execute(
            insert(ActiveCv)
            .values(user_id=user_id, version_id=version_id)
            .on_conflict_do_update(
                index_elements=[ActiveCv.user_id], set_={"version_id": version_id}
            )
        )
        self.session.add(
            CvAudit(
                user_id=user_id, document_id=row.document_id, version_id=row.id, action="ACTIVATE"
            )
        )

    async def export_version(self, user_id: UUID, version_id: UUID) -> dict[str, object]:
        """Caller transaction; selected version, not all account data."""
        await self.lock_owner(user_id)
        row = await self._row(user_id, version_id)
        original = await asyncio.to_thread(
            self.vault.read, VaultIdentity(user_id, row.document_id, row.id)
        )
        self.session.add(
            CvAudit(
                user_id=user_id, document_id=row.document_id, version_id=row.id, action="EXPORT"
            )
        )
        return {
            "version": (await self._view(row)).model_dump(mode="json"),
            "inspection": self._payload(row).inspection.model_dump(mode="json"),
            "original_base64": base64.b64encode(original.content).decode("ascii"),
        }

    async def delete_document(self, user_id: UUID, document_id: UUID) -> None:
        async with self.session.begin():
            await self.lock_owner(user_id)
            document = await self.session.scalar(
                select(CvDocument).where(
                    CvDocument.id == document_id, CvDocument.user_id == user_id
                )
            )
            if document is None:
                raise AppError("CV_NOT_FOUND", "CV document not found", 404)
            rows = list(
                (
                    await self.session.scalars(
                        select(CvVersion).where(
                            CvVersion.user_id == user_id, CvVersion.document_id == document_id
                        )
                    )
                ).all()
            )
            if any(row.state == "PUBLISHING" for row in rows):
                raise AppError("CV_STORAGE_BUSY", "CV publication must be recovered first", 409)
            document.state = "DELETING"
            for row in rows:
                row.state = "DELETING"
                await self.session.execute(
                    insert(CvStorageIntent)
                    .values(
                        id=uuid4(),
                        user_id=user_id,
                        document_id=document_id,
                        version_id=row.id,
                        kind="DELETE",
                        done=False,
                        created_at=utcnow(),
                    )
                    .on_conflict_do_nothing()
                )
        await self._purge(user_id, document_id)

    async def _purge(self, user_id: UUID, document_id: UUID) -> None:
        async with self.session.begin():
            await self.lock_owner(user_id)
            document = await self.session.get(CvDocument, document_id)
            if document is None or document.user_id != user_id or document.state != "DELETING":
                return
            intents = (
                await self.session.scalars(
                    select(CvStorageIntent).where(
                        CvStorageIntent.user_id == user_id,
                        CvStorageIntent.document_id == document_id,
                        CvStorageIntent.kind == "DELETE",
                        CvStorageIntent.done.is_(False),
                    )
                )
            ).all()
            for intent in intents:
                await asyncio.to_thread(
                    self.vault.remove, VaultIdentity(user_id, document_id, intent.version_id)
                )
                intent.done = True
            self.session.add(CvAudit(user_id=user_id, document_id=document_id, action="DELETE"))
            await asyncio.to_thread(
                self.vault.purge_pending, VaultIdentity(user_id, document_id, UUID(int=0))
            )
            await self.session.execute(delete(CvDocument).where(CvDocument.id == document_id))

    async def recover(self, user_id: UUID, *, age_seconds: int = 300) -> int:
        if age_seconds < 300:
            raise ValueError("Recovery grace must be at least 300 seconds")
        async with self.session.begin():
            await self.lock_owner(user_id)
            pending = list(
                (
                    await self.session.scalars(
                        select(CvStorageIntent)
                        .where(
                            CvStorageIntent.user_id == user_id,
                            CvStorageIntent.done.is_(False),
                            CvStorageIntent.created_at < utcnow() - timedelta(seconds=age_seconds),
                        )
                        .limit(200)
                    )
                ).all()
            )
            deletions = {p.document_id for p in pending if p.kind == "DELETE"}
            for intent in pending:
                if intent.kind != "PUBLISH":
                    continue
                row = await self.session.get(CvVersion, intent.version_id)
                if row is None or row.state != "PUBLISHING":
                    intent.done = True
                    continue
                try:
                    blob = await asyncio.to_thread(
                        self.vault.read, VaultIdentity(user_id, row.document_id, row.id)
                    )
                except AppError as error:
                    if error.code != "CV_FILE_NOT_FOUND":
                        raise
                    row.state, intent.done = "FAILED", True
                else:
                    if (
                        blob.filename != self._payload(row).filename
                        or len(blob.content) != row.byte_size
                    ):
                        raise AppError("CV_INTEGRITY_FAILED", "CV recovery integrity failed", 409)
                    await self._publish(user_id, row.id)
        for document_id in deletions:
            await self._purge(user_id, document_id)
        return len(pending)
