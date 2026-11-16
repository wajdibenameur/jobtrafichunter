import base64
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.private_payload import PrivatePayload
from app.core.settings import Settings
from app.modules.ai import JobInput, SkillDefinition, analyze_job
from app.modules.cv.private_data import PrivateCvData
from app.modules.matching.schemas import MatchingSnapshot, MatchJobInput, ScoringPolicy
from app.modules.matching.scoring import score_job
from app.modules.matching.service import MatchingService
from app.modules.profile import MatchingCandidate
from app.modules.profile.schemas import CandidateFields, CandidatePreferences
from app.modules.search.execution_schemas import ExecutionInput


def snapshot(**fields: object) -> MatchingSnapshot:
    return MatchingSnapshot(
        candidate=MatchingCandidate(
            id=uuid4(),
            cv_version_id=uuid4(),
            revision=1,
            fields=CandidateFields.model_validate(fields),
            preferences=CandidatePreferences(),
        ),
        taxonomy=[SkillDefinition(canonical="Python", category="languages", aliases=["Py"])],
        policy=ScoringPolicy(),
    )


def test_unknowns_and_title_alone_never_become_strong_matches() -> None:
    context = snapshot(professional_title="Python developer")
    job = MatchJobInput(id=uuid4(), group_id=uuid4(), title="Python developer")
    result = score_job(context, job, analyze_job(job, context.taxonomy))
    assert result.score == 10 and result.coverage == 10
    assert result.provisional and result.confidence == "LOW"
    assert result.calibration_status == "UNVALIDATED" and result.provider == "none"
    assert sum(p.points for p in result.components if p.name != "title") == 0


def test_aliases_repetition_missing_requirements_and_cap() -> None:
    context = snapshot(skills={"languages": ["Python", "Py", "Python"]})
    job = MatchJobInput(id=uuid4(), group_id=uuid4(), mandatory_skills=["Py", "Rust"])
    result = score_job(context, job, analyze_job(job, context.taxonomy))
    assert result.components[0].points == 17.5
    assert result.components[0].unattested == ["Rust"]
    assert "MANDATORY_SKILL_UNATTESTED" in result.cap_reasons
    context.policy = ScoringPolicy(
        weights={
            **context.policy.weights,
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
    job.mandatory_skills = ["Python", "Py", "Rust", "Go"]
    result = score_job(context, job, analyze_job(job, context.taxonomy))
    assert result.score == 33


def test_high_raw_score_is_capped_and_visa_is_never_inferred() -> None:
    context = snapshot(
        professional_title="Python developer",
        years_experience=3,
        skills={"languages": ["Python", "Angular"]},
        languages=["English C1"],
        education=["master"],
    )
    context.candidate.preferences = CandidatePreferences(locations=["Tunisia"], visa_needed=True)
    job = MatchJobInput(
        id=uuid4(),
        group_id=uuid4(),
        title="Python developer",
        country="Tunisia",
        mandatory_skills=["Python", "Rust"],
        optional_skills=["Angular"],
        min_years=2,
        max_years=4,
        visa_status="CONFIRMED",
        description="English C1 required\nmaster required",
    )
    result = score_job(context, job, analyze_job(job, context.taxonomy))
    assert result.uncapped_score == 83 and result.score == 60
    assert result.cap_reasons == ["MANDATORY_SKILL_UNATTESTED"]
    job.visa_status = "NOT_SPECIFIED"
    job.description = (job.description or "") + "\nVisa sponsorship available in this remote role"
    result = score_job(context, job, analyze_job(job, context.taxonomy))
    assert result.analysis.visa_status == "NOT_SPECIFIED"
    assert result.components[-1].state == "UNKNOWN" and result.components[-1].points == 0


@pytest.mark.parametrize(
    "description",
    [
        "Requirements\nPython\nPreferred\nPy",
        "Python required\nPython preferred",
    ],
)
def test_contradictory_unstructured_skill_is_not_asserted(description: str) -> None:
    context = snapshot()
    result = analyze_job(JobInput(id=uuid4(), description=description), context.taxonomy)
    assert not result.mandatory and not result.optional
    assert "CONTRADICTORY_SKILL:Python" in result.warnings


def test_bilingual_proofs_negation_and_optional_are_exact() -> None:
    text = "Prérequis\nPython requis, anglais C1, 3 ans expérience\nAtouts\nPython non requis\n"
    context = snapshot()
    result = analyze_job(JobInput(id=uuid4(), description=text), context.taxonomy)
    assert result.mandatory == ["Python"] and result.languages == ["English C1"]
    assert result.min_years == 3
    assert "NEGATED_REQUIREMENT" in result.warnings
    for proof in result.evidence:
        if proof.start is not None:
            assert text[proof.start : proof.end] == proof.quote
    assert (
        analyze_job(
            JobInput(id=uuid4(), description="Python is not required"), context.taxonomy
        ).mandatory
        == []
    )


def test_explicit_language_level_and_seniority_gaps_are_explained() -> None:
    context = snapshot(languages=["English B2"], years_experience=1)
    job = MatchJobInput(
        id=uuid4(), group_id=uuid4(), description="Required English C1 and 4 years experience"
    )
    result = score_job(context, job, analyze_job(job, context.taxonomy))
    assert "REQUIRED_LANGUAGE_UNATTESTED" in result.cap_reasons
    assert "SENIORITY_GAP" in result.cap_reasons and result.score <= 60
    context.candidate.fields.languages = ["English C2"]
    assert score_job(context, job, analyze_job(job, context.taxonomy)).components[4].points == 10


@pytest.mark.parametrize(
    "change",
    [
        {"mandatory_cap": 61},
        {"weights": {"mandatory": 100}},
        {"weights": {**ScoringPolicy().weights, "mandatory": 34}},
    ],
)
def test_invalid_policy_is_rejected(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ScoringPolicy.model_validate(change)


def test_rescore_requires_explicit_scope_and_no_collection_options() -> None:
    cases: list[dict[str, object]] = [
        {"scope": "MATCHING_ONLY"},
        {"policy_id": uuid4()},
        {
            "scope": "MATCHING_ONLY",
            "matching_preview": True,
            "source_execution_id": uuid4(),
            "max_results": 10,
        },
    ]
    for changes in cases:
        with pytest.raises(ValidationError):
            ExecutionInput.model_validate({"profile_id": uuid4(), **changes})


def test_legacy_cv_envelope_compatibility_and_namespace_separation() -> None:
    master, salt, nonce = bytes(range(32)), b"s" * 32, b"n" * 12
    context, text = b"fixture/owner/profile", b"SYNTHETIC_PRIVATE_FACT"
    key = SecretStr(base64.b64encode(master).decode())
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"jobhunter/cv/private-db/v1/" + context,
    ).derive(master)
    legacy = b"JHDB\x01" + salt + nonce + AESGCM(derived).encrypt(nonce, text, context)
    cv = PrivateCvData(key)
    assert cv.open(legacy, context) == text
    matching = PrivatePayload(
        key, namespace=b"jobhunter/matching/private-db/v1/", magic=b"JHMT\x01"
    )
    for payload, aad in [(legacy, context + b"other"), (legacy[:-1] + b"x", context)]:
        with pytest.raises(AppError):
            cv.open(payload, aad)
    with pytest.raises(AppError):
        matching.open(legacy, context)
    with pytest.raises(AppError):
        cv.seal(b"x" * (512 * 1024 + 1), context)
    assert matching.digest(text, b"owner-a") != matching.digest(text, b"owner-b")


def test_cache_key_tracks_all_frozen_inputs_and_owner(settings: Settings) -> None:
    service = MatchingService(AsyncSession(), settings)
    owner, context = uuid4(), snapshot(skills={"languages": ["Python"]})
    job = MatchJobInput(
        id=uuid4(), group_id=uuid4(), title="Developer", description="Required Python"
    )
    key = service.cache_key(owner, context, job)
    assert service.cache_key(owner, context.model_copy(deep=True), job.model_copy(deep=True)) == key
    changed = context.model_copy(deep=True)
    changed.candidate.fields.skills = {"languages": ["Rust"]}
    assert service.cache_key(owner, changed, job) != key
    changed = context.model_copy(deep=True)
    changed.candidate.revision += 1
    assert service.cache_key(owner, changed, job) != key
    changed = context.model_copy(deep=True)
    changed.taxonomy[0].revision += 1
    assert service.cache_key(owner, changed, job) != key
    changed = context.model_copy(deep=True)
    changed.policy.mandatory_cap = 50
    assert service.cache_key(owner, changed, job) != key
    for field, value in [
        ("description", "Optional Python"),
        ("country", "Tunisia"),
        ("visa_status", "NONE"),
        ("min_years", 10),
    ]:
        assert service.cache_key(owner, context, job.model_copy(update={field: value})) != key
    assert service.cache_key(uuid4(), context, job) != key
