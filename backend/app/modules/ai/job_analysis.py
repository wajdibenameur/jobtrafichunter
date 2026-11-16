"""Evidence-bound local job extraction. No network, provider or CV input."""

import hashlib
import json
import re
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ForeignKey, LargeBinary, String, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.private_payload import PrivatePayload
from app.core.settings import Settings
from app.modules.ai.taxonomy import SkillDefinition

EXTRACTOR_VERSION = "job-rules-v1"


class JobInput(BaseModel):
    model_config = ConfigDict(extra="ignore", hide_input_in_errors=True)
    id: UUID
    title: str | None = Field(default=None, max_length=300)
    company: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000, repr=False)
    mandatory_skills: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=100
    )
    optional_skills: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=100
    )
    min_years: int | None = Field(default=None, ge=0, le=60)
    max_years: int | None = Field(default=None, ge=0, le=60)
    experience_level: str | None = Field(default=None, max_length=50)
    domain: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    work_mode: str | None = Field(default=None, max_length=20)
    visa_status: str = "NOT_SPECIFIED"
    visa_evidence: str | None = Field(default=None, max_length=2000, repr=False)
    original_url: str = Field(default="", max_length=4096)
    application_url: str = Field(default="", max_length=4096)


class JobEvidence(BaseModel):
    field: str
    value: str
    start: int | None = None
    end: int | None = None
    quote: str = Field(default="", max_length=2000, repr=False)
    origin: str = "DESCRIPTION"


class JobAnalysis(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    mandatory: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    min_years: int | None = None
    max_years: int | None = None
    languages: list[str] = Field(default_factory=list)
    education: str | None = None
    visa_status: str = "NOT_SPECIFIED"
    evidence: list[JobEvidence] = Field(default_factory=list, repr=False)
    warnings: list[str] = Field(default_factory=list)
    provider: str = "none"
    extractor_version: str = EXTRACTOR_VERSION


class JobAnalysisRow(Base):
    __tablename__ = "job_analyses"
    __table_args__ = (UniqueConstraint("user_id", "cache_key", name="uq_job_analysis_cache"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[UUID]
    cache_key: Mapped[str] = mapped_column(String(64))
    extractor_version: Mapped[str] = mapped_column(String(50), default=EXTRACTOR_VERSION)
    private_payload: Mapped[bytes] = mapped_column(LargeBinary)


def content_hash(value: BaseModel | dict[str, object]) -> str:
    data = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def aliases(taxonomy: list[SkillDefinition]) -> dict[str, str]:
    return {
        label.casefold(): term.canonical
        for term in taxonomy
        for label in [term.canonical, *term.aliases]
    }


REQUIRED = re.compile(
    r"\b(required|mandatory|must|obligatoire|requis(?:e|es)?|exig[eé](?:e|es)?|indispensable)\b",
    re.I,
)
OPTIONAL = re.compile(
    r"\b(preferred|optional|nice to have|souhait[eé](?:e|es)?|atout|facultati[fv]e?)\b", re.I
)
NEGATED = re.compile(
    r"\b(not required|not mandatory|must not|no requirement|non requis|pas obligatoire|"
    r"sans exigence|ne .{0,30}pas|no .{0,60}required|not .{0,40}required)\b",
    re.I,
)
LANGUAGES = {
    "english": "English",
    "anglais": "English",
    "french": "French",
    "français": "French",
    "arabic": "Arabic",
    "arabe": "Arabic",
    "german": "German",
    "allemand": "German",
    "spanish": "Spanish",
    "espagnol": "Spanish",
}


def analyze_job(job: JobInput, taxonomy: list[SkillDefinition]) -> JobAnalysis:
    names = aliases(taxonomy)
    for label in [*job.mandatory_skills, *job.optional_skills]:
        names.setdefault(label.casefold(), label)
    # No unbounded regex/input from arbitrary URLs or external contexts.
    labels = sorted(names, key=len, reverse=True)
    pattern = (
        re.compile(r"(?<!\w)(?:" + "|".join(re.escape(v) for v in labels) + r")(?!\w)", re.I)
        if labels
        else None
    )
    required = {names.get(v.casefold(), v) for v in job.mandatory_skills}
    optional = {names.get(v.casefold(), v) for v in job.optional_skills}
    declared_required, declared_optional = set(required), set(optional)
    result = JobAnalysis(
        min_years=job.min_years, max_years=job.max_years, visa_status=job.visa_status
    )
    for field, values in (("mandatory", required), ("optional", optional)):
        result.evidence.extend(
            JobEvidence(field=field, value=v, origin="DECLARED_FIELD") for v in sorted(values)
        )
    match: re.Match[str] | None
    state, offset = "unknown", 0
    heading: tuple[int, str] | None = None
    for line in (job.description or "").splitlines(keepends=True):
        label = line.strip().strip(":- ").casefold()
        if label in {
            "requirements",
            "required skills",
            "qualifications",
            "prérequis",
            "profil recherché",
        }:
            state = "mandatory"
            heading = offset, line.rstrip()[:2000]
        elif label in {"preferred", "nice to have", "atouts"}:
            state = "optional"
            heading = offset, line.rstrip()[:2000]
        elif label in {"benefits", "avantages", "about us", "à propos"}:
            state = "unknown"
            heading = None
        elif line.rstrip().endswith(":"):
            state, heading = "unknown", None
        kind = (
            "optional" if OPTIONAL.search(line) else "mandatory" if REQUIRED.search(line) else state
        )
        if NEGATED.search(line):
            result.warnings.append("NEGATED_REQUIREMENT")
            offset += len(line)
            continue
        if (REQUIRED.search(line) and OPTIONAL.search(line)) or re.search(
            r"\b(or|ou)\b", line, re.I
        ):
            result.warnings.append("AMBIGUOUS_REQUIREMENT")
            offset += len(line)
            continue
        if kind in {"mandatory", "optional"}:
            marker = OPTIONAL.search(line) if kind == "optional" else REQUIRED.search(line)
            if len(result.evidence) < 300 and (marker or heading):
                begin, quote = (
                    (offset + marker.start(), marker.group()) if marker else heading or (0, "")
                )
                result.evidence.append(
                    JobEvidence(
                        field="requirement_context",
                        value=kind,
                        start=begin,
                        end=begin + len(quote),
                        quote=quote,
                    )
                )
            if pattern:
                for match in pattern.finditer(line):
                    canonical = names.get(match.group().casefold())
                    if canonical is None:
                        continue
                    (required if kind == "mandatory" else optional).add(canonical)
                    if len(result.evidence) < 300:
                        result.evidence.append(
                            JobEvidence(
                                field=kind,
                                value=canonical,
                                start=offset + match.start(),
                                end=offset + match.end(),
                                quote=match.group(),
                            )
                        )
            if kind == "mandatory":
                if result.min_years is None and re.search(r"exp[eé]rience", line, re.I):
                    match = re.search(
                        r"(?<!\d)(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\s*\+?\s*(?:years?|ans?)\b",
                        line,
                        re.I,
                    )
                    if match and int(match[1]) <= 60:
                        result.min_years = int(match[1])
                        if match[2] and result.min_years <= int(match[2]) <= 60:
                            result.max_years = int(match[2])
                        result.evidence.append(
                            JobEvidence(
                                field="min_years",
                                value=match[1],
                                start=offset + match.start(),
                                end=offset + match.end(),
                                quote=match.group(),
                            )
                        )
                for match in re.finditer(
                    r"\b(English|anglais|French|français|Arabic|arabe|German|allemand|Spanish|espagnol)\b(?:\s*[:(-]?\s*([ABC][12])\b)?",
                    line,
                    re.I,
                ):
                    language = LANGUAGES[match[1].casefold()] + (
                        " " + match[2].upper() if match[2] else ""
                    )
                    result.languages.append(language)
                    result.evidence.append(
                        JobEvidence(
                            field="languages",
                            value=language,
                            start=offset + match.start(),
                            end=offset + match.end(),
                            quote=match.group(),
                        )
                    )
                if result.education is None:
                    match = re.search(r"\b(master|bachelor|doctorat|phd|licence)\b", line, re.I)
                    if match:
                        result.education = match.group().casefold()
                        result.evidence.append(
                            JobEvidence(
                                field="education",
                                value=result.education,
                                start=offset + match.start(),
                                end=offset + match.end(),
                                quote=match.group(),
                            )
                        )
        offset += len(line)
    for conflict in required & optional:
        result.warnings.append("CONTRADICTORY_SKILL:" + conflict)
        if conflict in declared_required:
            optional.discard(conflict)
        elif conflict in declared_optional:
            required.discard(conflict)
        else:
            required.discard(conflict)
            optional.discard(conflict)
    result.mandatory, result.optional = sorted(required), sorted(optional)
    result.languages = sorted(set(result.languages))[:100]
    if len(result.evidence) > 300:
        result.warnings.append("EVIDENCE_LIMIT")
        result.evidence = result.evidence[:300]
    result.warnings = sorted(set(result.warnings))[:100]
    if not result.mandatory:
        result.warnings.append("MANDATORY_REQUIREMENTS_UNKNOWN")
    if not job.description:
        result.warnings.append("DESCRIPTION_MISSING")
    return result


class JobAnalysisService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.private = PrivatePayload(
            settings.cv_encryption_key,
            namespace=b"jobhunter/analysis/private-db/v1/",
            magic=b"JHJA\x01",
        )

    async def analyze(
        self,
        owner: UUID,
        job: JobInput,
        taxonomy: list[SkillDefinition],
        computed: JobAnalysis | None = None,
    ) -> tuple[UUID, JobAnalysis]:
        key = content_hash(
            {
                "job": job.model_dump(mode="json"),
                "taxonomy": [v.model_dump() for v in taxonomy],
                "extractor": EXTRACTOR_VERSION,
            }
        )
        # Caller serializes owner writes and owns the transaction; no nested commit.
        row = await self.session.scalar(
            select(JobAnalysisRow).where(
                JobAnalysisRow.user_id == owner, JobAnalysisRow.cache_key == key
            )
        )
        if row is not None:
            context = f"analysis/{owner}/{row.id}".encode()
            return row.id, JobAnalysis.model_validate_json(
                self.private.open(row.private_payload, context)
            )
        result = computed or analyze_job(job, taxonomy)
        identifier = uuid4()
        row = JobAnalysisRow(
            id=identifier,
            user_id=owner,
            listing_id=job.id,
            cache_key=key,
            private_payload=self.private.seal(
                result.model_dump_json().encode(), f"analysis/{owner}/{identifier}".encode()
            ),
        )
        self.session.add(row)
        await self.session.flush()
        return identifier, result
