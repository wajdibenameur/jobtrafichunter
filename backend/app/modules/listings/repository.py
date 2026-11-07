from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.listings.models import ImportBatch, ImportRecord, JobListing
from app.modules.listings.normalization import fingerprint
from app.modules.listings.schemas import ImportJob
from app.shared.clock import utcnow
from app.shared.source_reference import SourceReference
from app.shared.urls import canonical_url


class ListingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def import_one(
        self, user_id: UUID, source: SourceReference, job: ImportJob
    ) -> tuple[JobListing, bool]:
        url = canonical_url(job.original_url)
        values = job.model_dump(exclude_none=True)
        values.update(
            user_id=user_id,
            source_id=source.id,
            source_name=source.name,
            canonical_url=url,
            application_url=job.application_url or job.original_url,
            fingerprint=fingerprint(job.title, job.company, job.city, job.description, url),
        )
        inserted = await self.session.scalar(
            insert(JobListing).values(**values).on_conflict_do_nothing().returning(JobListing.id)
        )
        if inserted is not None:
            listing = await self.session.get(JobListing, inserted)
            assert listing is not None
            return listing, True
        identity = JobListing.canonical_url == url
        if job.source_job_id is not None:
            identity = or_(
                identity,
                (JobListing.source_id == source.id)
                & (JobListing.source_job_id == job.source_job_id),
            )
        rows = list(
            (
                await self.session.scalars(
                    select(JobListing)
                    .where(JobListing.user_id == user_id, identity)
                    .with_for_update()
                )
            ).all()
        )
        if len(rows) != 1:
            raise AppError(
                "IMPORT_CONFLICT", "Offer identifiers conflict; review the imported data", 409
            )
        listing = rows[0]
        editable = {
            "title",
            "company",
            "country",
            "city",
            "description",
            "work_mode",
            "domain",
            "experience_level",
            "min_years",
            "max_years",
            "mandatory_skills",
            "optional_skills",
            "visa_status",
            "visa_evidence",
            "published_at",
        }
        for field in job.model_fields_set & editable:
            value = getattr(job, field)
            if value is not None:
                setattr(listing, field, value)
        if "visa_status" in job.model_fields_set:
            listing.visa_evidence = job.visa_evidence
        if (
            listing.min_years is not None
            and listing.max_years is not None
            and listing.min_years > listing.max_years
        ):
            raise AppError(
                "IMPORT_REQUIREMENTS_CONFLICT", "Experience range conflicts with saved data", 422
            )
        listing.last_seen_at = utcnow()
        listing.fingerprint = fingerprint(
            listing.title, listing.company, listing.city, listing.description, listing.canonical_url
        )
        await self.session.flush()
        return listing, False

    async def record_batch(
        self, user_id: UUID, source_id: UUID, rows: list[tuple[JobListing, bool]]
    ) -> UUID:
        batch = ImportBatch(
            user_id=user_id,
            source_id=source_id,
            row_count=len(rows),
            created_count=sum(created for _, created in rows),
            existing_count=sum(not created for _, created in rows),
        )
        self.session.add(batch)
        await self.session.flush()
        for number, (listing, created) in enumerate(rows, start=1):
            self.session.add(
                ImportRecord(
                    batch_id=batch.id,
                    listing_id=listing.id,
                    row_number=number,
                    disposition="CREATED" if created else "EXISTING",
                )
            )
        return batch.id

    async def page(self, user_id: UUID, limit: int, offset: int) -> tuple[list[JobListing], int]:
        predicate = JobListing.user_id == user_id
        rows = list(
            (
                await self.session.scalars(
                    select(JobListing)
                    .where(predicate)
                    .order_by(JobListing.first_seen_at.desc(), JobListing.id)
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )
        count = await self.session.scalar(
            select(func.count()).select_from(JobListing).where(predicate)
        )
        return rows, int(count or 0)
