from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.listings.models import JobListing
from app.modules.listings.repository import ListingRepository
from app.modules.listings.schemas import ImportRequest, ImportResult, ListingsPage, ListingView
from app.shared.source_reference import SourceReference


def view(listing: JobListing) -> ListingView:
    return ListingView(
        id=listing.id,
        source_id=listing.source_id,
        source_name=listing.source_name,
        original_url=listing.original_url,
        canonical_url=listing.canonical_url,
        application_url=listing.application_url,
        title=listing.title,
        company=listing.company,
        country=listing.country,
        city=listing.city,
        description=listing.description,
        published_at=listing.published_at,
        first_seen_at=listing.first_seen_at,
        last_seen_at=listing.last_seen_at,
        visa_status=listing.visa_status,
        status=listing.status,
        missing_fields=[
            field
            for field in ("title", "company", "description", "published_at")
            if getattr(listing, field) is None
        ],
    )


class ListingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ListingRepository(session)

    async def import_jobs(
        self, user_id: UUID, source: SourceReference, body: ImportRequest
    ) -> ImportResult:
        if source.id != body.source_id or not source.manual_import_supported:
            raise AppError(
                "IMPORT_NOT_SUPPORTED", "Manual import is unavailable for this source", 409
            )
        async with self.session.begin():
            rows = [await self.repo.import_one(user_id, source, job) for job in body.jobs]
            batch_id = await self.repo.record_batch(user_id, source.id, rows)
            # Flush metadata before producing plain schemas; no ORM objects leave this layer.
            await self.session.flush()
            return ImportResult(
                batch_id=batch_id,
                created_count=sum(created for _, created in rows),
                existing_count=sum(not created for _, created in rows),
                listings=[view(listing) for listing, _ in rows],
            )

    async def page(self, user_id: UUID, limit: int, offset: int) -> ListingsPage:
        rows, count = await self.repo.page(user_id, limit, offset)
        return ListingsPage(items=[view(row) for row in rows], total=count)
