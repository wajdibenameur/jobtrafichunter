from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.errors import AppError


class SkillTerm(Base):
    __tablename__ = "skill_terms"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    canonical: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(50))
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list)
    revision: Mapped[int] = mapped_column(default=1)


class SkillDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    canonical: str = Field(min_length=1, max_length=100)
    category: Literal[
        "languages",
        "frameworks",
        "backend",
        "frontend",
        "databases",
        "devops",
        "cloud",
        "ai_ml",
        "data_engineering",
        "business_analysis",
        "other",
    ]
    aliases: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=20
    )
    revision: int = Field(default=1, ge=1)

    @field_validator("canonical")
    @classmethod
    def canonical_label(cls, value: str) -> str:
        if not value.strip() or "," in value or any(ord(c) < 32 for c in value):
            raise ValueError("Invalid skill label")
        return value.strip()

    @field_validator("aliases")
    @classmethod
    def alias_labels(cls, values: list[str]) -> list[str]:
        if any(not v.strip() or any(ord(c) < 32 for c in v) for v in values):
            raise ValueError("Invalid skill alias")
        return list(dict.fromkeys(v.strip() for v in values))


class TaxonomyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> list[SkillDefinition]:
        rows = (await self.session.scalars(select(SkillTerm).order_by(SkillTerm.canonical))).all()
        return [SkillDefinition.model_validate(row) for row in rows]

    async def set(self, definition: SkillDefinition) -> SkillDefinition:
        category_count = await self.session.scalar(
            select(func.count())
            .select_from(SkillTerm)
            .where(
                SkillTerm.category == definition.category,
                SkillTerm.canonical != definition.canonical,
            )
        )
        if category_count is not None and category_count >= 100:
            raise AppError("TAXONOMY_LIMIT", "At most 100 terms per category", 409)
        row = await self.session.scalar(
            select(SkillTerm).where(SkillTerm.canonical == definition.canonical).with_for_update()
        )
        if row is None:
            total = await self.session.scalar(select(func.count()).select_from(SkillTerm))
            if total is not None and total >= 200:
                raise AppError("TAXONOMY_LIMIT", "At most 200 skill terms", 409)
            row = SkillTerm(canonical=definition.canonical)
            self.session.add(row)
            row.revision = 1
        else:
            row.revision += 1
        row.category, row.aliases = definition.category, definition.aliases
        await self.session.flush()
        return SkillDefinition.model_validate(row)
