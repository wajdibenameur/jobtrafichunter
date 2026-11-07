from urllib.parse import urlencode
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.sources.models import JobSource
from app.modules.sources.policy import verified_automation
from app.modules.sources.repository import SourceRepository
from app.modules.sources.schemas import (
    SearchLinkRequest,
    SearchLinkView,
    SourceCreate,
    SourcePatch,
    SourceSettings,
    SourceView,
)
from app.shared.source_reference import SourceReference


class SourceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SourceRepository(session)

    async def _get(self, user_id: UUID, source_id: UUID) -> JobSource:
        row = await self.repo.get(user_id, source_id)
        if row is None:
            raise AppError("SOURCE_NOT_FOUND", "Source not found", 404)
        return row

    async def _view(self, user_id: UUID, row: JobSource) -> SourceView:
        preference = await self.repo.preference(user_id, row.id)
        manual = row.integration_type in {"LINK_ONLY", "MANUAL_IMPORT"}
        eligible = verified_automation(row.legal_status, row.verification)
        # This delivery has no automatic connector registered, even if a DB flag is edited.
        automation = False
        return SourceView(
            id=row.id,
            slug=row.slug,
            name=(preference.display_name if preference else None) or row.name,
            homepage=row.homepage,
            region=row.region,
            integration_type=row.integration_type,
            legal_status=row.legal_status if manual or eligible else "UNVERIFIED",
            enabled=preference.enabled if preference else False,
            automation_eligible=automation,
            manual_import_supported=manual,
            custom=row.user_id is not None,
            settings=SourceSettings.model_validate(preference.settings if preference else {}),
            health_status="MANUAL_ONLY"
            if manual
            else "DISABLED"
            if row.integration_type == "DISABLED"
            else "UNVERIFIED",
            reason="MANUAL_WORKFLOW" if manual else "AUTOMATION_NOT_CONFIGURED",
        )

    async def list(self, user_id: UUID) -> list[SourceView]:
        return [await self._view(user_id, row) for row in await self.repo.list(user_id)]

    async def patch(self, user_id: UUID, source_id: UUID, body: SourcePatch) -> SourceView:
        async with self.session.begin():
            row = await self._get(user_id, source_id)
            if body.enabled is True and row.integration_type not in {"LINK_ONLY", "MANUAL_IMPORT"}:
                raise AppError("AUTOMATION_NOT_PERMITTED", "Automatic source is unavailable", 409)
            values: dict[str, object] = body.model_dump(exclude_none=True)
            if values:
                await self.repo.save_preference(user_id, source_id, values)
            return await self._view(user_id, row)

    async def create(self, user_id: UUID, body: SourceCreate) -> SourceView:
        async with self.session.begin():
            if len(await self.repo.list(user_id)) >= 100:
                raise AppError("SOURCE_LIMIT", "At most 100 visible sources are supported", 409)
            row = JobSource(
                user_id=user_id,
                slug="custom-" + uuid4().hex,
                name=body.name.strip(),
                homepage=body.homepage,
                region=body.region,
                integration_type="LINK_ONLY",
                legal_status="LINK_ONLY",
                search_strategy="homepage",
            )
            await self.repo.add(row)
            return await self._view(user_id, row)

    async def delete(self, user_id: UUID, source_id: UUID) -> None:
        async with self.session.begin():
            row = await self._get(user_id, source_id)
            if row.user_id != user_id:
                raise AppError(
                    "SOURCE_TEMPLATE", "Disable built-in sources instead of deleting them", 409
                )
            row.archived = True

    async def resolve(self, user_id: UUID, source_id: UUID) -> SourceReference:
        row = await self._get(user_id, source_id)
        return SourceReference(
            row.id, row.name, row.integration_type in {"LINK_ONLY", "MANUAL_IMPORT"}
        )

    async def search_link(
        self, user_id: UUID, source_id: UUID, body: SearchLinkRequest
    ) -> SearchLinkView:
        row = await self._get(user_id, source_id)
        if row.search_strategy == "linkedin":
            url = "https://www.linkedin.com/jobs/search/?" + urlencode(
                {"keywords": body.keywords, "location": body.location}
            )
        elif row.search_strategy == "indeed":
            url = "https://www.indeed.com/jobs?" + urlencode(
                {"q": body.keywords, "l": body.location}
            )
        elif row.search_strategy == "tanitjobs":
            url = "https://www.tanitjobs.com/jobs/?" + urlencode(
                {
                    "keywords[all_words]": body.keywords,
                    "GooglePlace[location][value]": body.location,
                    "action": "search",
                    "listing_type[equal]": "Job",
                }
            )
        elif row.search_strategy == "keejob":
            keywords = " ".join(part for part in (body.keywords, body.location) if part.strip())
            url = "https://www.keejob.com/offres-emploi/?" + urlencode({"keywords": keywords})
        else:
            return SearchLinkView(url=row.homepage, criteria_applied=False)
        return SearchLinkView(url=url, criteria_applied=True)
