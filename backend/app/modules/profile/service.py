import asyncio
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.settings import Settings
from app.modules.ai import TaxonomyService
from app.modules.cv import CvService, PrivateCvData
from app.modules.profile.extraction import propose_profile
from app.modules.profile.models import ActiveCandidateProfile, CandidateProfileVersion
from app.modules.profile.schemas import CandidateInput, CandidateView, ProfilePayload
from app.shared.clock import utcnow


class ProfileService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.cv = CvService(session, settings)
        self.private = PrivateCvData(settings.cv_encryption_key)

    @staticmethod
    def _context(user: UUID, identifier: UUID) -> bytes:
        return f"candidate/{user}/{identifier}".encode()

    def _payload(self, row: CandidateProfileVersion) -> ProfilePayload:
        return ProfilePayload.model_validate_json(
            self.private.open(row.private_payload, self._context(row.user_id, row.id))
        )

    async def _row(self, user: UUID, identifier: UUID) -> CandidateProfileVersion:
        row = await self.session.scalar(
            select(CandidateProfileVersion).where(
                CandidateProfileVersion.id == identifier, CandidateProfileVersion.user_id == user
            )
        )
        if row is None:
            raise AppError("CANDIDATE_NOT_FOUND", "Candidate profile not found", 404)
        return row

    async def _view(self, row: CandidateProfileVersion) -> CandidateView:
        data = self._payload(row)
        active = await self.session.get(ActiveCandidateProfile, row.user_id)
        previous = await self._row(row.user_id, row.parent_id) if row.parent_id else None
        previous_data = self._payload(previous) if previous else None
        before = previous_data.fields.model_dump() if previous_data else {}
        before_preferences = previous_data.preferences.model_dump() if previous_data else {}
        fields = data.fields.model_dump()
        return CandidateView(
            id=row.id,
            cv_version_id=row.cv_version_id,
            parent_id=row.parent_id,
            revision=row.revision,
            status=row.status,
            active=active is not None and active.profile_id == row.id,
            created_at=row.created_at,
            validated_at=row.validated_at,
            data=data,
            changed_fields=[key for key, value in fields.items() if before.get(key) != value]
            + [
                "preferences." + key
                for key, value in data.preferences.model_dump().items()
                if before_preferences.get(key) != value
            ],
            unknown_fields=[
                key for key, value in fields.items() if value is None or value == [] or value == {}
            ],
        )

    async def list(self, user: UUID, cv_version: UUID) -> list[CandidateView]:
        await self.cv.get_version(user, cv_version)
        rows = (
            await self.session.scalars(
                select(CandidateProfileVersion)
                .where(
                    CandidateProfileVersion.user_id == user,
                    CandidateProfileVersion.cv_version_id == cv_version,
                )
                .order_by(CandidateProfileVersion.revision.desc())
                .limit(100)
            )
        ).all()
        return [await self._view(row) for row in rows]

    async def get(self, user: UUID, identifier: UUID) -> CandidateView:
        return await self._view(await self._row(user, identifier))

    async def validated_active(self, user: UUID) -> CandidateView:
        active = await self.session.get(ActiveCandidateProfile, user)
        if active is None:
            raise AppError("CANDIDATE_NOT_ACTIVE", "No validated candidate profile is active", 409)
        row = await self._row(user, active.profile_id)
        if row.status != "VALIDATED":
            raise AppError("CANDIDATE_NOT_VALIDATED", "Candidate profile requires review", 409)
        return await self._view(row)

    async def _new(
        self, user: UUID, cv_version: UUID, data: ProfilePayload, parent: UUID | None
    ) -> CandidateView:
        latest = int(
            await self.session.scalar(
                select(func.max(CandidateProfileVersion.revision)).where(
                    CandidateProfileVersion.cv_version_id == cv_version,
                    CandidateProfileVersion.user_id == user,
                )
            )
            or 0
        )
        if latest >= 100:
            raise AppError("CANDIDATE_LIMIT", "At most 100 candidate revisions per CV", 409)
        identifier = uuid4()
        row = CandidateProfileVersion(
            id=identifier,
            user_id=user,
            cv_version_id=cv_version,
            revision=latest + 1,
            parent_id=parent,
            private_payload=self.private.seal(
                data.model_dump_json().encode(), self._context(user, identifier)
            ),
        )
        self.session.add(row)
        await self.session.flush()
        return await self._view(row)

    async def generate(self, user: UUID, cv_version: UUID, regenerate: bool) -> CandidateView:
        async with self.session.begin():
            await self.cv.lock_owner(user)
            document = await self.cv.get_version(user, cv_version)
            existing = await self.list(user, cv_version)
            if existing and not regenerate:
                return existing[0]
            parent = existing[0].id if existing else None
            if parent is None:
                versions = await self.cv.list(user)
                previous_cv_ids = [
                    v.id for v in versions if v.document_id == document.version.document_id
                ]
                previous = await self.session.scalar(
                    select(CandidateProfileVersion)
                    .where(
                        CandidateProfileVersion.user_id == user,
                        CandidateProfileVersion.cv_version_id.in_(previous_cv_ids),
                    )
                    .order_by(CandidateProfileVersion.created_at.desc())
                    .limit(1)
                )
                parent = previous.id if previous else None
            return await self._new(
                user,
                cv_version,
                await asyncio.to_thread(
                    propose_profile, document.inspection, await TaxonomyService(self.session).list()
                ),
                parent,
            )

    async def edit(self, user: UUID, identifier: UUID, body: CandidateInput) -> CandidateView:
        async with self.session.begin():
            await self.cv.lock_owner(user)
            original = await self._row(user, identifier)
            await self.cv.get_version(user, original.cv_version_id)
            data = self._payload(original)
            old, updated = data.fields.model_dump(), body.fields.model_dump()
            for key, value in updated.items():
                if value != old[key]:
                    for proof in list(data.evidence):
                        if proof == key or proof.startswith(key + "."):
                            data.evidence.pop(proof)
                            data.origins.pop(proof, None)
                    data.origins[key] = "USER_EDITED"
            for key, value in body.preferences.model_dump().items():
                if value != data.preferences.model_dump()[key]:
                    data.origins["preferences." + key] = "USER_PREFERENCE"
            data.fields, data.preferences = body.fields, body.preferences
            return await self._new(user, original.cv_version_id, data, original.id)

    async def validate(self, user: UUID, identifier: UUID) -> CandidateView:
        async with self.session.begin():
            await self.cv.lock_owner(user)
            row = await self._row(user, identifier)
            await self.cv.get_version(user, row.cv_version_id)
            fields = self._payload(row).fields
            if not any(value for value in fields.model_dump().values()):
                raise AppError("CANDIDATE_EMPTY", "Review and fill candidate facts first", 422)
            row.status, row.validated_at = "VALIDATED", row.validated_at or utcnow()
            await self.session.flush()
            return await self._view(row)

    async def activate(self, user: UUID, identifier: UUID) -> CandidateView:
        async with self.session.begin():
            await self.cv.lock_owner(user)
            row = await self._row(user, identifier)
            if row.status != "VALIDATED":
                raise AppError("CANDIDATE_NOT_VALIDATED", "Validate candidate profile first", 409)
            await self.cv.activate_validated(user, row.cv_version_id)
            await self.session.execute(
                insert(ActiveCandidateProfile)
                .values(
                    user_id=user,
                    profile_id=row.id,
                )
                .on_conflict_do_update(
                    index_elements=[ActiveCandidateProfile.user_id], set_={"profile_id": row.id}
                )
            )
            return await self._view(row)
