"""Offline evaluation only: owner labels never change application scoring state."""

import json
import math
import os
import stat
from collections import Counter, defaultdict
from pathlib import Path
from typing import Annotated, Literal, Self, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    ValidationError,
    field_validator,
    model_validator,
)

from app.modules.ai import JobAnalysis, content_hash
from app.modules.matching.schemas import (
    MatchingSnapshot,
    MatchJobInput,
    MatchPreview,
    ScoringPolicy,
)
from app.modules.matching.service import MatchingService
from app.modules.profile import MatchingCandidate

MAX_BYTES = 20 * 1024 * 1024
Label = Literal["NO", "WEAK", "GOOD", "STRONG"]
Domain = Literal[
    "JAVA_SPRING_ANGULAR", "DEVOPS", "DATA_ENGINEERING", "AI", "BUSINESS_ANALYSIS", "OTHER"
]
LABEL_RANK: dict[Label, int] = {"NO": 0, "WEAK": 1, "GOOD": 2, "STRONG": 3}
TARGET_DOMAINS = {"JAVA_SPRING_ANGULAR", "DEVOPS", "DATA_ENGINEERING", "AI", "BUSINESS_ANALYSIS"}
Key = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")]


class CalibrationError(Exception):
    """Only a stable, data-free code may leave the CLI boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class CalibrationCandidate(MatchingCandidate):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    @model_validator(mode="after")
    def minimal_facts(self) -> Self:
        if self.fields.summary or self.fields.experiences or self.fields.certifications:
            raise ValueError("Use minimal anonymized matching facts")
        return self


class CalibrationSnapshot(MatchingSnapshot):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    candidate: CalibrationCandidate = Field(repr=False)
    candidate_reviewed: Literal[True]

    @field_validator("candidate_reviewed", mode="before")
    @classmethod
    def explicit_review(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit candidate review required")
        return value


class CalibrationJob(MatchJobInput):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    visa_status: Literal["CONFIRMED", "POSSIBLE", "RELOCATION", "NOT_SPECIFIED", "NONE"] = (
        "NOT_SPECIFIED"
    )
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None

    @model_validator(mode="after")
    def years_consistent(self) -> Self:
        if (
            self.min_years is not None
            and self.max_years is not None
            and self.max_years < self.min_years
        ):
            raise ValueError("Inconsistent experience range")
        return self


class CalibrationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    case_id: Key
    candidate_key: Key
    job: CalibrationJob = Field(repr=False)
    label: Label
    domain: Domain
    mandatory_gap_notes: str = Field(default="", max_length=2000, repr=False)


class CalibrationCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    schema_version: Literal[1]
    purpose: Literal["SYNTHETIC", "TUNING", "VALIDATION"]
    owner_reviewed: StrictBool = False
    snapshots: dict[Key, CalibrationSnapshot] = Field(
        default_factory=dict, max_length=20, repr=False
    )
    cases: list[CalibrationCase] = Field(default_factory=list, max_length=1000, repr=False)

    @field_validator("schema_version", mode="before")
    @classmethod
    def version_number(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Integer format version required")
        return value

    @model_validator(mode="after")
    def consistent_cases(self) -> Self:
        ids: set[str] = set()
        pairs: set[tuple[str, str]] = set()
        groups: dict[str, str] = {}
        for case in self.cases:
            snapshot = self.snapshots.get(case.candidate_key)
            if snapshot is None or case.case_id in ids:
                raise ValueError("Missing reference or duplicate case")
            cohort = content_hash(snapshot)
            group = str(case.job.group_id)
            pair = cohort, group
            if pair in pairs:
                raise ValueError("Duplicate labelled pair")
            job_data = case.job.model_dump(mode="json", exclude={"id", "group_id"})
            fingerprint = content_hash(job_data)
            if group in groups and groups[group] != fingerprint:
                raise ValueError("Conflicting job snapshots")
            ids.add(case.case_id)
            pairs.add(pair)
            groups[group] = fingerprint
        return self


def local_path(value: str | Path) -> Path:
    raw = os.fspath(value)
    if raw.startswith(("\\\\", "//")) or "://" in raw:
        raise CalibrationError("CALIBRATION_LOCAL_PATH_REQUIRED")
    return Path(raw)


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CalibrationError("CALIBRATION_JSON_INVALID")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise CalibrationError("CALIBRATION_JSON_INVALID")


Model = TypeVar("Model", bound=BaseModel)


def load_model(path: str | Path, model: type[Model]) -> Model:
    """Bound bytes before JSON parsing; reject devices, duplicate keys and nonfinite JSON."""
    try:
        target = local_path(path)
        descriptor = os.open(
            target, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        )
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise CalibrationError("CALIBRATION_REGULAR_FILE_REQUIRED")
            if info.st_size > MAX_BYTES:
                raise CalibrationError("CALIBRATION_FILE_LIMIT")
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise CalibrationError("CALIBRATION_FILE_LIMIT")
        json.loads(raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=_constant)
        # JSON mode accepts UUID strings while rejecting numeric/string coercions.
        return model.model_validate_json(raw, strict=True)
    except CalibrationError:
        raise
    except (OSError, UnicodeError):
        raise CalibrationError("CALIBRATION_FILE_UNAVAILABLE") from None
    except (ValueError, ValidationError, RecursionError):
        raise CalibrationError("CALIBRATION_DATA_INVALID") from None


class Rate(BaseModel):
    count: int
    denominator: int
    value: float | None


class Metrics(BaseModel):
    count: int
    label_counts: dict[str, int]
    spearman: float | None
    spearman_reason: str | None
    precision_k: int
    precision_at_k: float | None
    no_above_60: Rate
    no_above_70: Rate
    strong_below_60: Rate


def average_ranks(values: list[int]) -> list[float]:
    ranks = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in ordered[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def metrics(scores: list[int], labels: list[Label]) -> Metrics:
    if (
        len(scores) != len(labels)
        or any(type(v) is not int or not 0 <= v <= 100 for v in scores)
        or any(v not in LABEL_RANK for v in labels)
    ):
        raise CalibrationError("CALIBRATION_SCORES_INVALID")
    count = len(scores)
    x, y = average_ranks(scores), average_ranks([LABEL_RANK[label] for label in labels])
    correlation: float | None = None
    reason: str | None = "INSUFFICIENT_PAIRS"
    if count >= 2:
        mx, my = sum(x) / count, sum(y) / count
        xx, yy = sum((v - mx) ** 2 for v in x), sum((v - my) ** 2 for v in y)
        if xx == 0 or yy == 0:
            reason = "ZERO_VARIANCE"
        else:
            correlation = max(
                -1.0,
                min(
                    1.0,
                    sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
                    / math.sqrt(xx * yy),
                ),
            )
            reason = None
    k, relevant = min(10, count), 0.0
    if k:
        boundary = sorted(scores, reverse=True)[k - 1]
        above = sum(v > boundary for v in scores)
        tied = sum(v == boundary for v in scores)
        for score, label in zip(scores, labels, strict=True):
            if label in {"GOOD", "STRONG"}:
                relevant += (
                    1 if score > boundary else (k - above) / tied if score == boundary else 0
                )
    counts = Counter(labels)

    def rate(label: Label, predicate: list[bool]) -> Rate:
        hits = sum(
            passed and actual == label for passed, actual in zip(predicate, labels, strict=True)
        )
        denominator = counts[label]
        return Rate(
            count=hits, denominator=denominator, value=hits / denominator if denominator else None
        )

    return Metrics(
        count=count,
        label_counts={label: counts[label] for label in LABEL_RANK},
        spearman=correlation,
        spearman_reason=reason,
        precision_k=k,
        precision_at_k=relevant / k if k else None,
        no_above_60=rate("NO", [v > 60 for v in scores]),
        no_above_70=rate("NO", [v > 70 for v in scores]),
        strong_below_60=rate("STRONG", [v < 60 for v in scores]),
    )


class Evaluation(BaseModel):
    policy: ScoringPolicy
    metrics: Metrics
    capped_count: int
    target_status: Literal["INCOMPLETE", "TARGETS_NOT_MET", "TARGETS_MET"]
    reasons: list[str]


class Comparison(BaseModel):
    increased: int
    decreased: int
    unchanged: int
    mean_score_delta: float | None


class CohortReport(BaseModel):
    cohort: int
    distinct_groups: int
    distinct_contents: int
    domain_counts: dict[str, int]
    baseline: Evaluation
    alternative: Evaluation | None
    comparison: Comparison | None


class CalibrationReport(BaseModel):
    report_version: Literal[1] = 1
    corpus_format_version: Literal[1] = 1
    calibration_status: Literal["UNVALIDATED"] = "UNVALIDATED"
    human_validation_required: Literal[True] = True
    purpose: Literal["SYNTHETIC", "TUNING", "VALIDATION"]
    scoring_version: str
    extractor_version: str
    provider: Literal["none"] = "none"
    ties: Literal["AVERAGE_RANKS_AND_FRACTIONAL_TOP_K"] = "AVERAGE_RANKS_AND_FRACTIONAL_TOP_K"
    case_count: int
    cohort_count: int
    cohorts: list[CohortReport]


def _scores(snapshot: MatchingSnapshot, cases: list[CalibrationCase]) -> tuple[list[int], int]:
    scores, capped = [], 0
    for start in range(0, len(cases), 20):
        for item in MatchingService.compute(
            snapshot, [case.job for case in cases[start : start + 20]]
        ):
            scores.append(item.preview.score)
            capped += item.preview.score < item.preview.uncapped_score
    return scores, capped


def _evaluation(
    corpus: CalibrationCorpus,
    snapshot: MatchingSnapshot,
    cases: list[CalibrationCase],
    policy: ScoringPolicy,
    content_count: int,
    domains: Counter[str],
) -> tuple[Evaluation, list[int]]:
    labels = [case.label for case in cases]
    frozen = snapshot.model_copy(update={"policy": policy}, deep=True)
    scores, capped = _scores(frozen, cases)
    measured = metrics(scores, labels)
    reasons = []
    if corpus.purpose != "VALIDATION":
        reasons.append("VALIDATION_CORPUS_REQUIRED")
    if not corpus.owner_reviewed:
        reasons.append("OWNER_REVIEW_REQUIRED")
    if content_count < 50:
        reasons.append("FIFTY_DISTINCT_OFFERS_REQUIRED")
    if content_count < len(cases):
        reasons.append("REPEATED_JOB_CONTENT")
    if not TARGET_DOMAINS.issubset(domains):
        reasons.append("TARGET_DOMAINS_INCOMPLETE")
    if any(measured.label_counts[label] == 0 for label in LABEL_RANK):
        reasons.append("LABEL_CLASSES_INCOMPLETE")
    if measured.spearman is None:
        reasons.append("CORRELATION_UNDEFINED")
    state: Literal["INCOMPLETE", "TARGETS_NOT_MET", "TARGETS_MET"] = "INCOMPLETE"
    if not reasons:
        failed = (
            measured.spearman is None or measured.spearman < 0.6 or measured.no_above_70.count > 0
        )
        state = "TARGETS_NOT_MET" if failed else "TARGETS_MET"
        if failed:
            reasons.append("INITIAL_TARGETS_NOT_MET")
    return Evaluation(
        policy=policy,
        metrics=measured,
        capped_count=capped,
        target_status=state,
        reasons=reasons,
    ), scores


def evaluate(
    corpus: CalibrationCorpus, alternative: ScoringPolicy | None = None
) -> CalibrationReport:
    grouped: dict[str, list[CalibrationCase]] = defaultdict(list)
    for case in corpus.cases:
        grouped[content_hash(corpus.snapshots[case.candidate_key])].append(case)
    reports = []
    for index, key in enumerate(sorted(grouped), start=1):
        cases = sorted(grouped[key], key=lambda case: case.case_id)
        snapshot = corpus.snapshots[cases[0].candidate_key]
        # Exact-copy diagnostic, not a replacement for catalog deduplication.
        contents = {
            content_hash(
                case.job.model_dump(
                    mode="json", exclude={"id", "group_id", "original_url", "application_url"}
                )
            )
            for case in cases
        }
        domains: Counter[str] = Counter(case.domain for case in cases)

        baseline, scores = _evaluation(
            corpus, snapshot, cases, snapshot.policy, len(contents), domains
        )
        changed, comparison = None, None
        if alternative is not None:
            changed, rescored = _evaluation(
                corpus, snapshot, cases, alternative, len(contents), domains
            )
            deltas = [b - a for a, b in zip(scores, rescored, strict=True)]
            comparison = Comparison(
                increased=sum(v > 0 for v in deltas),
                decreased=sum(v < 0 for v in deltas),
                unchanged=sum(v == 0 for v in deltas),
                mean_score_delta=sum(deltas) / len(deltas) if deltas else None,
            )
        reports.append(
            CohortReport(
                cohort=index,
                distinct_groups=len(cases),
                distinct_contents=len(contents),
                domain_counts={
                    domain: domains[domain] for domain in sorted(TARGET_DOMAINS | {"OTHER"})
                },
                baseline=baseline,
                alternative=changed,
                comparison=comparison,
            )
        )
    return CalibrationReport(
        purpose=corpus.purpose,
        case_count=len(corpus.cases),
        cohort_count=len(reports),
        cohorts=reports,
        scoring_version=str(MatchPreview.model_fields["scoring_version"].default),
        extractor_version=str(JobAnalysis.model_fields["extractor_version"].default),
    )
