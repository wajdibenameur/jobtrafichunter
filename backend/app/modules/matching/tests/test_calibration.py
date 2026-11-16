"""Synthetic mathematical fixtures only; no real calibration labels or quality claim."""

import json
from pathlib import Path
from typing import Literal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.modules.matching import calibration as subject
from app.modules.matching.calibration import (
    CalibrationCase,
    CalibrationCorpus,
    CalibrationError,
    Label,
    average_ranks,
    evaluate,
    load_model,
    metrics,
)
from app.modules.matching.schemas import MatchingSnapshot, ScoringPolicy


def synthetic_corpus(
    count: int = 4, *, purpose: Literal["SYNTHETIC", "TUNING", "VALIDATION"] = "SYNTHETIC"
) -> CalibrationCorpus:
    """Distinct synthetic jobs and ordinal labels; never an owner-labelled corpus."""
    return CalibrationCorpus.model_validate(
        {
            "schema_version": 1,
            "purpose": purpose,
            "owner_reviewed": False,
            "snapshots": {
                "synthetic_profile": {
                    "candidate_reviewed": True,
                    "candidate": {
                        "id": str(UUID(int=1)),
                        "cv_version_id": str(UUID(int=2)),
                        "revision": 1,
                        "fields": {
                            "professional_title": "SYNTHETIC_PRIVATE_TITLE",
                            "skills": {"languages": ["Python"]},
                        },
                        "preferences": {},
                    },
                    "taxonomy": [{"canonical": "Python", "category": "languages"}],
                    "policy": {},
                }
            },
            "cases": [
                {
                    "case_id": f"synthetic_{index:04}",
                    "candidate_key": "synthetic_profile",
                    "job": {
                        "id": str(UUID(int=100 + index)),
                        "group_id": str(UUID(int=200 + index)),
                        "title": f"Synthetic posting {index}",
                        "description": "SYNTHETIC_PRIVATE_DESCRIPTION",
                        "mandatory_skills": ["Python"],
                    },
                    "label": ["NO", "WEAK", "GOOD", "STRONG"][index % 4],
                    "domain": sorted(subject.TARGET_DOMAINS)[index % 5],
                    "mandatory_gap_notes": "SYNTHETIC_PRIVATE_NOTES",
                }
                for index in range(count)
            ],
        }
    )


def test_spearman_uses_average_tie_ranks_and_handles_inverted_ranking() -> None:
    assert average_ranks([30, 10, 10, 90]) == [3, 1.5, 1.5, 4]
    assert metrics([10, 10, 90, 90], ["NO", "NO", "STRONG", "STRONG"]).spearman == pytest.approx(1)
    assert metrics([100, 80, 40, 0], ["NO", "WEAK", "GOOD", "STRONG"]).spearman == pytest.approx(-1)
    # Closed-form hand calculation: Pearson of ranks (1,2.5,2.5,4) and (1,2,3,4).
    assert metrics([0, 50, 50, 100], ["NO", "WEAK", "GOOD", "STRONG"]).spearman == pytest.approx(
        4.5 / (4.5 * 5) ** 0.5
    )


@pytest.mark.parametrize(
    ("scores", "labels", "reason"),
    [
        ([], [], "INSUFFICIENT_PAIRS"),
        ([60], ["STRONG"], "INSUFFICIENT_PAIRS"),
        ([50, 50], ["NO", "STRONG"], "ZERO_VARIANCE"),
        ([10, 90], ["GOOD", "GOOD"], "ZERO_VARIANCE"),
    ],
)
def test_undefined_correlation_never_becomes_a_success(
    scores: list[int], labels: list[Label], reason: str
) -> None:
    result = metrics(scores, labels)
    assert result.spearman is None and result.spearman_reason == reason


def test_top_ten_boundary_ties_are_fractional_and_permutation_invariant() -> None:
    scores = [100] * 8 + [50] * 4
    labels: list[Label] = [
        "GOOD",
        "GOOD",
        "GOOD",
        "GOOD",
        "GOOD",
        "GOOD",
        "GOOD",
        "GOOD",
        "STRONG",
        "NO",
        "STRONG",
        "NO",
    ]
    result = metrics(scores, labels)
    assert result.precision_k == 10 and result.precision_at_k == pytest.approx(0.9)
    assert metrics(scores[::-1], labels[::-1]) == result
    assert metrics([1, 2, 3], ["NO", "GOOD", "STRONG"]).precision_at_k == pytest.approx(2 / 3)
    assert metrics([], []).precision_at_k is None


def test_rates_use_category_denominators_and_strict_thresholds() -> None:
    measured = metrics(
        [60, 61, 70, 71, 59, 60, 61], ["NO", "NO", "NO", "NO", "STRONG", "STRONG", "STRONG"]
    )
    assert measured.no_above_60.model_dump() == {"count": 3, "denominator": 4, "value": 0.75}
    assert measured.no_above_70.value == 0.25
    assert measured.strong_below_60.count == 1 and measured.strong_below_60.denominator == 3
    absent = metrics([50, 70], ["WEAK", "GOOD"])
    assert absent.no_above_60.value is None and absent.no_above_60.denominator == 0
    assert absent.strong_below_60.value is None


def test_invalid_scores_are_rejected() -> None:
    cases: list[list[int]] = [[-1], [101], [True], []]
    for scores in cases:
        with pytest.raises(CalibrationError):
            metrics(scores, ["NO"])


def test_comparison_reuses_actual_scorer_and_does_not_mutate_inputs() -> None:
    corpus = synthetic_corpus()
    before = corpus.model_dump_json()
    policy = ScoringPolicy(
        weights={
            "mandatory": 100,
            "optional": 0,
            "experience": 0,
            "title": 0,
            "languages": 0,
            "location": 0,
            "education": 0,
            "visa": 0,
        }
    )
    report = evaluate(corpus, policy)
    assert corpus.model_dump_json() == before
    row = report.cohorts[0]
    assert row.comparison and row.comparison.increased == 4
    assert row.comparison.mean_score_delta == 65
    assert row.baseline.metrics.spearman is None  # actual scorer yields equal synthetic scores
    assert row.baseline.target_status == "INCOMPLETE"
    assert report.calibration_status == "UNVALIDATED" and report.human_validation_required
    assert "SYNTHETIC_PRIVATE" not in report.model_dump_json()


def test_cohorts_are_separate_and_report_order_is_reproducible() -> None:
    corpus = synthetic_corpus()
    other = corpus.snapshots["synthetic_profile"].model_copy(deep=True)
    other.candidate.revision = 2
    other.candidate.id = UUID(int=3)
    corpus.snapshots["another_profile"] = other
    corpus.cases[0].candidate_key = "another_profile"
    first = evaluate(corpus)
    corpus.cases.reverse()
    assert evaluate(corpus) == first and first.cohort_count == 2
    assert sorted(c.baseline.metrics.count for c in first.cohorts) == [1, 3]


@pytest.mark.parametrize(
    "violation",
    [
        "missing_reference",
        "duplicate_case",
        "duplicate_pair",
        "conflicting_job",
        "extra_job_field",
        "invalid_years",
        "unreviewed_candidate",
        "private_summary",
        "long_note",
    ],
)
def test_corpus_consistency_and_privacy_bounds(violation: str) -> None:
    data = synthetic_corpus().model_dump(mode="json")
    if violation == "missing_reference":
        data["cases"][0]["candidate_key"] = "absent"
    elif violation == "duplicate_case":
        data["cases"][1]["case_id"] = data["cases"][0]["case_id"]
    elif violation == "duplicate_pair":
        data["cases"][1]["job"] = data["cases"][0]["job"]
    elif violation == "conflicting_job":
        other = json.loads(json.dumps(data["snapshots"]["synthetic_profile"]))
        other["candidate"]["revision"] = 2
        other["candidate"]["id"] = str(UUID(int=3))
        data["snapshots"]["other"] = other
        data["cases"][1]["candidate_key"] = "other"
        data["cases"][1]["job"]["group_id"] = data["cases"][0]["job"]["group_id"]
    elif violation == "extra_job_field":
        data["cases"][0]["job"]["unexpected"] = "private"
    elif violation == "invalid_years":
        data["cases"][0]["job"].update(min_years=5, max_years=2)
    elif violation == "unreviewed_candidate":
        data["snapshots"]["synthetic_profile"]["candidate_reviewed"] = False
    elif violation == "private_summary":
        data["snapshots"]["synthetic_profile"]["candidate"]["fields"]["summary"] = "private contact"
    else:
        data["cases"][0]["mandatory_gap_notes"] = "x" * 2001
    with pytest.raises(ValidationError):
        CalibrationCorpus.model_validate(data)


def synthetic_scores(
    snapshot: MatchingSnapshot, cases: list[CalibrationCase]
) -> tuple[list[int], int]:
    # Deliberate numeric fixture for the gate mechanics; NOT a quality measurement.
    return [subject.LABEL_RANK[case.label] * 30 for case in cases], 0


def test_target_gate_never_promotes_state_or_accepts_incomplete_corpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "_scores", synthetic_scores)
    corpus = synthetic_corpus(50, purpose="VALIDATION")
    corpus.owner_reviewed = True
    report = evaluate(corpus)
    assert report.cohorts[0].baseline.target_status == "TARGETS_MET"
    assert report.calibration_status == "UNVALIDATED"
    corpus.purpose = "TUNING"
    assert evaluate(corpus).cohorts[0].baseline.target_status == "INCOMPLETE"
    corpus.purpose, corpus.owner_reviewed = "VALIDATION", False
    assert "OWNER_REVIEW_REQUIRED" in evaluate(corpus).cohorts[0].baseline.reasons
    corpus.owner_reviewed = True
    corpus.cases = corpus.cases[:49]
    assert "FIFTY_DISTINCT_OFFERS_REQUIRED" in evaluate(corpus).cohorts[0].baseline.reasons


def test_target_failures_and_repeated_content_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = synthetic_corpus(50, purpose="VALIDATION")
    corpus.owner_reviewed = True

    def inverted(snapshot: MatchingSnapshot, cases: list[CalibrationCase]) -> tuple[list[int], int]:
        return [100 - subject.LABEL_RANK[case.label] * 30 for case in cases], 0

    monkeypatch.setattr(subject, "_scores", inverted)
    result = evaluate(corpus).cohorts[0]
    assert result.baseline.target_status == "TARGETS_NOT_MET"
    assert result.baseline.metrics.no_above_70.count > 0
    for case in corpus.cases:
        case.job.title = "Identical copied posting"
    assert "REPEATED_JOB_CONTENT" in evaluate(corpus).cohorts[0].baseline.reasons


@pytest.mark.parametrize(
    "text",
    [
        '{"schema_version":1,"schema_version":1}',
        '{"value":NaN}',
        '{"value":Infinity}',
        "{",
        "[" * 2000,
    ],
)
def test_loader_masks_invalid_json_and_rejects_nonfinite_or_duplicate_keys(
    tmp_path: Path, text: str
) -> None:
    source = tmp_path / "synthetic.json"
    source.write_text(text, encoding="utf-8")
    with pytest.raises(CalibrationError) as error:
        load_model(source, CalibrationCorpus)
    assert text not in str(error.value)


def test_loader_enforces_file_limit_before_parsing(tmp_path: Path) -> None:
    source = tmp_path / "large.json"
    with source.open("wb") as stream:
        stream.truncate(subject.MAX_BYTES + 1)
    with pytest.raises(CalibrationError, match="CALIBRATION_FILE_LIMIT"):
        load_model(source, CalibrationCorpus)
    with pytest.raises(CalibrationError):
        load_model(tmp_path, CalibrationCorpus)


@pytest.mark.parametrize(
    "violation",
    [
        "version_bool",
        "version_float",
        "review_number",
        "too_many_cases",
        "too_many_snapshots",
        "missing_class",
        "missing_domain",
    ],
)
def test_format_limits_and_incomplete_category_coverage(violation: str) -> None:
    data = synthetic_corpus().model_dump(mode="json")
    if violation == "version_bool":
        data["schema_version"] = True
    elif violation == "version_float":
        data["schema_version"] = 1.0
    elif violation == "review_number":
        data["snapshots"]["synthetic_profile"]["candidate_reviewed"] = 1
    elif violation == "too_many_cases":
        data["cases"] *= 251
    elif violation == "too_many_snapshots":
        data["snapshots"] = {
            f"p{index}": data["snapshots"]["synthetic_profile"] for index in range(21)
        }
    elif violation == "missing_class":
        for case in data["cases"]:
            case["label"] = "GOOD"
        report = evaluate(CalibrationCorpus.model_validate(data))
        assert "LABEL_CLASSES_INCOMPLETE" in report.cohorts[0].baseline.reasons
        return
    else:
        for case in data["cases"]:
            case["domain"] = "OTHER"
        report = evaluate(CalibrationCorpus.model_validate(data))
        assert "TARGET_DOMAINS_INCOMPLETE" in report.cohorts[0].baseline.reasons
        return
    with pytest.raises(ValidationError):
        CalibrationCorpus.model_validate(data)


def test_public_schema_and_empty_template_stay_in_sync() -> None:
    root = Path(__file__).resolve().parents[5]
    schema = json.loads((root / "calibration/schema.json").read_text(encoding="utf-8"))
    assert schema == CalibrationCorpus.model_json_schema()
    empty = load_model(root / "calibration/template.json", CalibrationCorpus)
    assert not empty.cases and not empty.owner_reviewed
    assert not evaluate(empty).cohorts


def test_json_loader_rejects_coercions_but_accepts_uuid_strings(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.json"
    corpus = synthetic_corpus()
    path.write_text(corpus.model_dump_json(), encoding="utf-8")
    assert load_model(path, CalibrationCorpus) == corpus
    raw = corpus.model_dump(mode="json")
    raw["cases"][0]["job"]["min_years"] = "2"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(CalibrationError):
        load_model(path, CalibrationCorpus)


@pytest.mark.parametrize("violation", ["duplicate_across_policies", "conflicting_candidate"])
def test_candidate_identity_and_labels_do_not_depend_on_policy(violation: str) -> None:
    raw = synthetic_corpus().model_dump(mode="json")
    other = json.loads(json.dumps(raw["snapshots"]["synthetic_profile"]))
    other["policy"]["mandatory_cap"] = 50
    raw["snapshots"]["other"] = other
    if violation == "duplicate_across_policies":
        raw["cases"][1]["candidate_key"] = "other"
        raw["cases"][1]["job"] = raw["cases"][0]["job"]
        raw["cases"][1]["label"] = "STRONG"
    else:
        other["candidate"]["fields"]["professional_title"] = "Changed immutable candidate"
    with pytest.raises(ValidationError):
        CalibrationCorpus.model_validate(raw)
