"""Experimental deterministic scoring: unknowns earn no redistributed points."""

import re
from decimal import ROUND_HALF_UP, Decimal

from app.modules.ai import JobAnalysis, aliases
from app.modules.matching.schemas import MatchingSnapshot, MatchJobInput, MatchPreview, ScorePart


def score_job(
    snapshot: MatchingSnapshot, job: MatchJobInput, analysis: JobAnalysis
) -> MatchPreview:
    candidate, policy = snapshot.candidate, snapshot.policy
    alias = aliases(snapshot.taxonomy)

    def normalize(value: str) -> str:
        return alias.get(value.casefold(), value).casefold()

    skills = {normalize(v) for values in candidate.fields.skills.values() for v in values}
    components: list[ScorePart] = []
    reasons: list[str] = []

    def part(
        name: str,
        fraction: Decimal | None,
        *,
        conflict: bool = False,
        matched: list[str] | None = None,
        unattested: list[str] | None = None,
    ) -> None:
        points = (Decimal(policy.weights[name]) * (fraction or Decimal(0))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        components.append(
            ScorePart(
                name=name,
                weight=policy.weights[name],
                points=float(points),
                state="UNKNOWN" if fraction is None else "CONFLICT" if conflict else "KNOWN",
                matched=matched or [],
                unattested=unattested or [],
            )
        )

    for name, requirements in (("mandatory", analysis.mandatory), ("optional", analysis.optional)):
        found = [v for v in requirements if normalize(v) in skills]
        missing = [v for v in requirements if normalize(v) not in skills]
        known = bool(requirements) and bool(skills)
        part(
            name,
            Decimal(len(found)) / len(requirements) if known else None,
            matched=found,
            unattested=missing if requirements else [],
        )
        if name == "mandatory" and missing:
            reasons.append("MANDATORY_SKILL_UNATTESTED")

    years, minimum, maximum = (
        candidate.fields.years_experience,
        analysis.min_years,
        analysis.max_years,
    )
    if minimum is None or years is None:
        part("experience", None)
        if minimum is not None:
            reasons.append("EXPERIENCE_UNATTESTED")
    else:
        fraction = (
            min(Decimal(1), Decimal(str(years)) / Decimal(minimum)) if minimum else Decimal(1)
        )
        mismatch = years < minimum or (maximum is not None and years > maximum)
        part("experience", fraction, conflict=mismatch)
        if minimum - years > 1 or (maximum is not None and years - maximum > 1):
            reasons.append("SENIORITY_GAP")

    def tokens(value: str) -> set[str]:
        return {v.casefold() for v in re.findall(r"[\w+#]+", value) if len(v) > 2} - {
            "senior",
            "junior",
            "remote",
            "the",
            "and",
            "avec",
            "pour",
            "les",
            "des",
        }

    wanted, actual = tokens(job.title or ""), tokens(candidate.fields.professional_title or "")
    part("title", Decimal(len(wanted & actual)) / len(wanted) if wanted and actual else None)

    languages = " ".join(candidate.fields.languages).casefold()
    matched_languages: list[str] = []
    missing_languages: list[str] = []
    language_aliases = {
        "English": ["english", "anglais"],
        "French": ["french", "français"],
        "Arabic": ["arabic", "arabe"],
        "German": ["german", "allemand"],
        "Spanish": ["spanish", "espagnol"],
    }
    for requirement in analysis.languages:
        language, _, level = requirement.partition(" ")
        values = [
            v.casefold()
            for v in candidate.fields.languages
            if any(
                re.search(r"\b" + re.escape(alias) + r"\b", v, re.I)
                for alias in language_aliases[language]
            )
        ]
        levels = [
            m.group().upper() for value in values for m in re.finditer(r"\b[abc][12]\b", value)
        ]
        order = ["A1", "A2", "B1", "B2", "C1", "C2"]
        passed = bool(values) and (
            not level or any(order.index(v) >= order.index(level) for v in levels)
        )
        (matched_languages if passed else missing_languages).append(requirement)
    part(
        "languages",
        Decimal(len(matched_languages)) / len(analysis.languages)
        if analysis.languages and languages
        else None,
        matched=matched_languages,
        unattested=missing_languages,
    )
    if missing_languages:
        reasons.append("REQUIRED_LANGUAGE_UNATTESTED")

    locations = {v.casefold() for v in candidate.preferences.locations}
    declared_locations = [v for v in (job.country, job.city) if v]
    location_match = [v for v in declared_locations if v.casefold() in locations]
    part(
        "location",
        Decimal(bool(location_match)) if locations and declared_locations else None,
        matched=location_match,
    )
    education = analysis.education
    has_education = bool(
        education
        and any(
            re.search(r"\b" + re.escape(education) + r"\b", v, re.I)
            for v in candidate.fields.education
        )
    )
    part(
        "education",
        Decimal(has_education) if education and candidate.fields.education else None,
        unattested=[education] if education and not has_education else [],
    )
    if education and not has_education:
        reasons.append("REQUIRED_EDUCATION_UNATTESTED")
    needed = candidate.preferences.visa_needed
    known_visa = needed is not None and analysis.visa_status in {"CONFIRMED", "NONE"}
    visa_ok = not needed or analysis.visa_status == "CONFIRMED"
    part("visa", Decimal(visa_ok) if known_visa else None, conflict=known_visa and not visa_ok)
    if known_visa and not visa_ok:
        reasons.append("SPONSORSHIP_MISMATCH")

    raw = int(
        sum((Decimal(str(p.points)) for p in components), Decimal(0)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    return MatchPreview(
        score=min(raw, policy.mandatory_cap) if reasons else raw,
        uncapped_score=raw,
        coverage=sum(p.weight for p in components if p.state != "UNKNOWN"),
        components=components,
        cap_reasons=sorted(set(reasons)),
        warnings=sorted(
            set([*analysis.warnings, "UNCALIBRATED", "PREFERENCES_ARE_NOT_WORK_AUTHORIZATION"])
        ),
        analysis=analysis,
    )
