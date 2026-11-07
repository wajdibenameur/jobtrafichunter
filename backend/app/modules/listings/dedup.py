import hashlib
import re
import unicodedata
from dataclasses import dataclass

from app.modules.listings.search_contracts import ListingFact


def normalized(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").casefold()
    return " ".join(re.findall(r"\w+", "".join(c for c in text if not unicodedata.combining(c))))


def identity_key(title: str | None, company: str | None, city: str | None) -> str:
    return hashlib.sha256(
        "\0".join(normalized(v) for v in (title, company, city)).encode()
    ).hexdigest()


@dataclass(frozen=True)
class DedupPolicy:
    version: str = "conservative-v1"
    merge_threshold: float = 0.95
    candidate_threshold: float = 0.75
    min_description_chars: int = 80

    def __post_init__(self) -> None:
        if not 0 < self.candidate_threshold < self.merge_threshold <= 1:
            raise ValueError("Dedup thresholds must be ordered within (0, 1]")
        if self.min_description_chars < 40:
            raise ValueError("Descriptions must provide enough evidence")


def relation(left: ListingFact, right: ListingFact, policy: DedupPolicy) -> str | None:
    """Evidence-based grouping only; missing identity never proves equivalence."""
    if left.canonical_url == right.canonical_url:
        return "DUPLICATE"
    identity = ("title", "company", "city")
    if any(
        not normalized(getattr(left, field))
        or normalized(getattr(left, field)) != normalized(getattr(right, field))
        for field in identity
    ):
        return None
    if left.country and right.country and normalized(left.country) != normalized(right.country):
        return None
    a, b = normalized(left.description), normalized(right.description)
    if min(len(a), len(b)) < policy.min_description_chars:
        return None
    a_words, b_words = set(a.split()), set(b.split())
    similarity = len(a_words & b_words) / len(a_words | b_words)
    if similarity < policy.candidate_threshold:
        return None
    if similarity < policy.merge_threshold:
        return "CANDIDATE"
    if left.published_at and right.published_at and left.published_at != right.published_at:
        return "REPOST"
    # Dates unknown on different URLs cannot rule out a republication.
    if left.published_at is None or right.published_at is None:
        return "CANDIDATE"
    return "DUPLICATE"
