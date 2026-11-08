from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.modules.listings import ListingGroupView
from app.modules.listings.tests.test_dedup import fact
from app.modules.search.filters import filter_fact
from app.modules.search.schemas import SearchCriteria


@pytest.mark.parametrize("minutes", [120, 360, 1440])
@pytest.mark.parametrize("offset,accepted", [(-1, True), (0, False), (1, False)])
def test_hourly_cutoff_is_strict(minutes: int, offset: int, accepted: bool) -> None:
    now = datetime(2026, 11, 8, 12, tzinfo=UTC)
    listing = fact(published_at=now - timedelta(minutes=minutes, microseconds=offset))
    group = ListingGroupView(
        id=listing.id,
        members=[listing],
        provenance=[],
        candidate_ids=[],
        repost_of_id=None,
        first_seen_at=listing.first_seen_at,
        policy_version="test",
    )
    criteria = SearchCriteria.model_validate({"publication_minutes": minutes})
    assert filter_fact(listing, group, criteria, now).accepted is accepted


@pytest.mark.parametrize("minutes", [120, 360, 1440])
@pytest.mark.parametrize("kind", ["unknown", "future", "now"])
def test_unknown_future_and_current_dates(minutes: int, kind: str) -> None:
    now = datetime(2026, 11, 8, 12, tzinfo=UTC)
    value = None if kind == "unknown" else now + timedelta(seconds=1 if kind == "future" else 0)
    listing = fact(published_at=value)
    group = ListingGroupView(
        id=listing.id,
        members=[listing],
        provenance=[],
        candidate_ids=[],
        repost_of_id=None,
        first_seen_at=now,
        policy_version="test",
    )
    criteria = SearchCriteria.model_validate(
        {"publication_minutes": minutes, "unknown_policy": "include"}
    )
    result = filter_fact(listing, group, criteria, now)
    assert result.accepted is (kind == "now")
    assert ("published_at" in result.unknown_fields) is (kind == "unknown")


@pytest.mark.parametrize("days", [1, 7, 30])
@pytest.mark.parametrize("kind", ["boundary", "unknown"])
def test_legacy_day_windows_keep_inclusive_cutoffs_and_unknown_policy(days: int, kind: str) -> None:
    now = datetime(2026, 11, 8, 12, tzinfo=UTC)
    listing = fact(published_at=now - timedelta(days=days) if kind == "boundary" else None)
    group = ListingGroupView(
        id=listing.id,
        members=[listing],
        provenance=[],
        candidate_ids=[],
        repost_of_id=None,
        first_seen_at=now,
        policy_version="test",
    )
    criteria = SearchCriteria.model_validate(
        {"publication_days": days, "unknown_policy": "include"}
    )
    assert criteria.publication_minutes is None
    assert filter_fact(listing, group, criteria, now).accepted


@pytest.mark.parametrize("zone", ["Europe/Paris", "Africa/Tunis"])
@pytest.mark.parametrize("month", [3, 10])
def test_timezone_display_cannot_change_elapsed_time(zone: str, month: int) -> None:
    now = datetime(2026, month, 29 if month == 3 else 25, 2, 30, tzinfo=UTC)
    listing = fact(published_at=(now - timedelta(minutes=119)).astimezone(ZoneInfo(zone)))
    group = ListingGroupView(
        id=listing.id,
        members=[listing],
        provenance=[],
        candidate_ids=[],
        repost_of_id=None,
        first_seen_at=now,
        policy_version="test",
    )
    assert filter_fact(listing, group, SearchCriteria(publication_minutes=120), now).accepted


def test_conflicting_windows_and_invalid_minutes_are_rejected() -> None:
    for values in ({"publication_minutes": 120, "publication_days": 7}, {"publication_minutes": 2}):
        with pytest.raises(ValidationError):
            SearchCriteria.model_validate(values)
    assert SearchCriteria().publication_minutes is None and SearchCriteria().publication_days == 0
