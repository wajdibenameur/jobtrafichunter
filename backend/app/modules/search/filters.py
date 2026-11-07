from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.modules.listings import ListingFact, ListingGroupView
from app.modules.search.schemas import SearchCriteria


def normalized(value: str) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", value).casefold()
    return " ".join(re.findall(r"\w+", "".join(c for c in text if not unicodedata.combining(c))))


COUNTRIES = {
    "tn": "tunisia",
    "tunisie": "tunisia",
    "fr": "france",
    "de": "germany",
    "allemagne": "germany",
    "deutschland": "germany",
    "pt": "portugal",
    "belgique": "belgium",
    "be": "belgium",
    "pays bas": "netherlands",
    "uk": "united kingdom",
    "royaume uni": "united kingdom",
}


def country(value: str) -> str:
    clean = normalized(value)
    return COUNTRIES.get(clean, clean)


@dataclass(frozen=True)
class FilterDecision:
    accepted: bool
    unknown_fields: list[str]
    rejected_fields: list[str]


def filter_fact(
    fact: ListingFact, group: ListingGroupView, criteria: SearchCriteria, now: datetime
) -> FilterDecision:
    unknown: list[str] = []
    rejected: list[str] = []
    fields: list[tuple[str, Sequence[str]]] = [
        ("country", criteria.countries),
        ("city", criteria.cities),
        ("work_mode", criteria.work_modes),
        ("domain", criteria.domains),
        ("experience_level", criteria.experience_levels),
    ]
    for field, choices in fields:
        if not choices:
            continue
        value = getattr(fact, field)
        if not value:
            unknown.append(field)
        else:
            clean = country if field == "country" else normalized
            if clean(value) not in {clean(choice) for choice in choices}:
                rejected.append(field)
    if fact.min_years is not None:
        if fact.min_years > criteria.max_years:
            rejected.append("experience_years")
    elif fact.max_years is None or fact.max_years > criteria.max_years:
        unknown.append("experience_years")
    text = " ".join(
        normalized(value or "")
        for value in (
            fact.title,
            fact.description,
            " ".join(fact.mandatory_skills + fact.optional_skills),
        )
    )

    def contains(term: str, haystack: str = text) -> bool:
        return f" {normalized(term)} " in f" {haystack} "

    if criteria.titles and not any(
        contains(term, normalized(fact.title or "")) for term in criteria.titles
    ):
        (rejected if fact.title else unknown).append("title")
    if criteria.include_keywords and not any(contains(term) for term in criteria.include_keywords):
        (rejected if fact.description else unknown).append("include_keywords")
    if criteria.exclude_keywords:
        if any(contains(term) for term in criteria.exclude_keywords):
            rejected.append("exclude_keywords")
        elif not fact.description:
            unknown.append("description_exclusions")
    if criteria.visa_statuses and fact.visa_status not in criteria.visa_statuses:
        rejected.append("visa_status")
    if criteria.publication_days:
        if fact.published_at is None:
            unknown.append("published_at")
        elif (
            fact.published_at < now - timedelta(days=criteria.publication_days)
            or fact.published_at > now
        ):
            rejected.append("published_at")
    if criteria.novelty != "all":
        if not group.novelty_verified:
            unknown.append("novelty")
        else:
            cutoff = (
                now.astimezone(ZoneInfo("Europe/Paris")).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                if criteria.novelty == "today"
                else now - timedelta(days={"24h": 1, "3d": 3, "7d": 7, "30d": 30}[criteria.novelty])
            )
            if group.first_seen_at < cutoff or group.first_seen_at > now:
                rejected.append("first_seen_at")
    if criteria.unknown_policy == "exclude":
        rejected.extend(unknown)
    return FilterDecision(not rejected, sorted(set(unknown)), sorted(set(rejected)))
