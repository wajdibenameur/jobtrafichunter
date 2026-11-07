from datetime import UTC, datetime

from app.modules.listings import ListingGroupView
from app.modules.listings.tests.test_dedup import fact
from app.modules.search.filters import filter_fact
from app.modules.search.schemas import SearchCriteria


def test_real_requirements_unknowns_and_keywords() -> None:
    listing = fact(title="Junior Python", min_years=5)
    group = ListingGroupView(
        id=listing.id,
        members=[listing],
        provenance=[],
        candidate_ids=[],
        repost_of_id=None,
        first_seen_at=listing.first_seen_at,
        policy_version="test",
    )
    now = datetime(2026, 11, 7, 12, tzinfo=UTC)
    assert not filter_fact(listing, group, SearchCriteria(), now).accepted
    listing = listing.model_copy(update={"min_years": None, "description": None})
    result = filter_fact(listing, group, SearchCriteria(include_keywords=["Python"]), now)
    assert result.accepted and "experience_years" in result.unknown_fields
    assert not filter_fact(listing, group, SearchCriteria(unknown_policy="exclude"), now).accepted
    assert not filter_fact(
        listing, group, SearchCriteria(exclude_keywords=["Python"]), now
    ).accepted
    assert not filter_fact(
        listing, group, SearchCriteria(visa_statuses=["CONFIRMED"]), now
    ).accepted
    assert filter_fact(listing, group, SearchCriteria(countries=["Tunisie"]), now).accepted
    assert not filter_fact(listing, group, SearchCriteria(countries=["France"]), now).accepted


def test_paris_today_in_winter_and_summer_and_publication_is_distinct() -> None:
    for month, hour in [(11, 23), (7, 22)]:
        now = datetime(2026, month, 7, hour, 30, tzinfo=UTC)
        listing = fact(first_seen_at=now, published_at=None)
        group = ListingGroupView(
            id=listing.id,
            members=[listing],
            provenance=[],
            candidate_ids=[],
            repost_of_id=None,
            first_seen_at=now.replace(minute=1),
            policy_version="test",
        )
        criteria = SearchCriteria(novelty="today", publication_days=1)
        result = filter_fact(listing, group, criteria, now)
        assert result.accepted and "published_at" in result.unknown_fields
        group.first_seen_at = now.replace(hour=hour - 1)
        assert not filter_fact(listing, group, criteria, now).accepted
        group.novelty_verified = False
        assert "novelty" in filter_fact(listing, group, criteria, now).unknown_fields
