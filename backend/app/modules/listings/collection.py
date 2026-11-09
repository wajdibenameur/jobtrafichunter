"""Collected observations never overwrite confirmed manual content."""

import hashlib
import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.listings.models import CollectionObservation, CollectionPage
from app.modules.listings.repository import ListingRepository
from app.modules.listings.schemas import ImportJob
from app.shared.source_reference import SourceReference


class CollectedJob(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    job: ImportJob
    metadata: dict[str, object]

    @field_validator("metadata")
    @classmethod
    def bounded_metadata(cls, value: dict[str, object]) -> dict[str, object]:
        if len(json.dumps(value, ensure_ascii=True)) > 150000:
            raise ValueError("Collection metadata exceeds limit")
        return value


class CollectionPageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    execution_id: UUID
    checkpoint_id: UUID
    source_id: UUID
    source_name: str = Field(max_length=100)
    request_key: str = Field(pattern=r"^[a-f0-9]{64}$")
    query_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    items: list[CollectedJob] = Field(max_length=500)


class CollectionReceipt(BaseModel):
    page_id: UUID
    created: int
    existing: int


async def ingest_collection_page(
    session: AsyncSession, user_id: UUID, page: CollectionPageInput
) -> CollectionReceipt:
    # Caller owns transaction and has fenced its execution. Same lock as manual import.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": user_id.int & ((1 << 63) - 1)}
    )
    prior = await session.scalar(
        select(CollectionPage).where(
            CollectionPage.user_id == user_id,
            CollectionPage.execution_id == page.execution_id,
            CollectionPage.source_id == page.source_id,
            CollectionPage.request_key == page.request_key,
        )
    )
    if prior is not None:
        if prior.query_hash != page.query_hash:
            raise AppError("COLLECTION_CONFLICT", "Page identity changed", 409)
        return CollectionReceipt.model_validate(prior.receipt)
    row = CollectionPage(
        user_id=user_id,
        source_id=page.source_id,
        execution_id=page.execution_id,
        checkpoint_id=page.checkpoint_id,
        request_key=page.request_key,
        query_hash=page.query_hash,
        payload_hash=hashlib.sha256(page.model_dump_json().encode()).hexdigest(),
        receipt={},
    )
    session.add(row)
    await session.flush()
    created = 0
    repo = ListingRepository(session)
    source = SourceReference(page.source_id, page.source_name, False)
    for position, item in enumerate(page.items):
        listing, inserted = await repo.import_one(user_id, source, item.job, enrich=False)
        created += inserted
        session.add(
            CollectionObservation(
                page_id=row.id,
                position=position,
                listing_id=listing.id,
                payload=item.model_dump(mode="json"),
            )
        )
    receipt = CollectionReceipt(page_id=row.id, created=created, existing=len(page.items) - created)
    row.receipt = receipt.model_dump(mode="json")
    await session.flush()
    return receipt
