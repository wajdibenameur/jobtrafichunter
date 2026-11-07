from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.core.db import Runtime
from app.modules.auth import AuthService
from app.modules.listings.catalog import ListingCatalog
from app.modules.listings.dedup import DedupPolicy, normalized, relation
from app.modules.listings.schemas import ImportJob, ImportRequest
from app.modules.listings.search_contracts import ListingFact
from app.modules.listings.service import ListingService
from app.modules.sources import SourceService

DESCRIPTION = (
    "Python backend development with PostgreSQL APIs testing integration services "
    "security teamwork and reliable delivery of production software."
)


def fact(**overrides: object) -> ListingFact:
    values: dict[str, object] = dict(
        id=uuid4(),
        source_id=uuid4(),
        source_name="Fixture",
        source_job_id=None,
        original_url="https://example.test/a",
        canonical_url="https://example.test/" + str(uuid4()),
        application_url="https://example.test/a",
        title="Développeur Python",
        company="Company",
        city="Tunis",
        country="Tunisia",
        work_mode=None,
        domain=None,
        experience_level=None,
        min_years=None,
        max_years=None,
        description=DESCRIPTION,
        mandatory_skills=[],
        optional_skills=[],
        visa_status="NOT_SPECIFIED",
        visa_evidence=None,
        published_at=datetime(2026, 11, 1, tzinfo=UTC),
        first_seen_at=datetime(2026, 11, 7, tzinfo=UTC),
        last_seen_at=datetime(2026, 11, 7, tzinfo=UTC),
        status="ACTIVE",
    )
    values.update(overrides)
    return ListingFact.model_validate(values)


def test_strong_identity_dates_and_unknowns() -> None:
    left = fact()
    policy = DedupPolicy()
    assert normalized("  Développeur-PYTHON ") == "developpeur python"
    assert relation(left, fact(title="Developpeur Python"), policy) == "DUPLICATE"
    assert relation(left, fact(city="Sfax"), policy) is None
    assert relation(left, fact(company="Other"), policy) is None
    assert relation(left, fact(country="France"), policy) is None
    assert relation(left, fact(description=None), policy) is None
    assert relation(left, fact(title=None), policy) is None
    assert relation(left, fact(published_at=None), policy) == "CANDIDATE"
    assert left.published_at is not None
    assert (
        relation(left, fact(published_at=left.published_at + timedelta(days=2)), policy) == "REPOST"
    )
    assert relation(left, fact(description="Unrelated advertisement " * 10), policy) is None
    assert (
        relation(left, fact(description=DESCRIPTION + " additional unique optional words"), policy)
        == "CANDIDATE"
    )
    assert (
        relation(left, fact(canonical_url=left.canonical_url, description=None), policy)
        == "DUPLICATE"
    )


@pytest.mark.parametrize(
    "kwargs", [{"merge_threshold": 2}, {"candidate_threshold": 1}, {"min_description_chars": 1}]
)
def test_policy_rejects_unsafe_thresholds(kwargs: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        DedupPolicy(**kwargs)  # type: ignore[arg-type]


@pytest.mark.integration
async def test_persistent_group_all_provenance_and_old_discovery(database: Runtime) -> None:
    async with database.sessions() as session:
        user = (
            await AuthService(session, database.settings).setup_owner(
                "dedup@example.test", "fixture-password-for-dedup"
            )
        ).id
    source_ids = [
        UUID("10000000-0000-4000-8000-000000000001"),
        UUID("10000000-0000-4000-8000-000000000003"),
    ]
    seen = []
    for i, source_id in enumerate(source_ids):
        async with database.sessions() as session:
            source = await SourceService(session).resolve(user, source_id)
        async with database.sessions() as session:
            imported = await ListingService(session).import_jobs(
                user,
                source,
                ImportRequest(
                    source_id=source_id,
                    confirm=True,
                    jobs=[
                        ImportJob(
                            original_url=f"https://example.test/{i}",
                            title="Python",
                            company="Company",
                            city="Tunis",
                            description=DESCRIPTION,
                            published_at=datetime(2026, 11, 1, tzinfo=UTC),
                        )
                    ],
                ),
            )
            seen.append(imported.listings[0].first_seen_at)
    async with database.sessions() as session:
        result = await ListingCatalog(session).scan(user, source_ids)
    assert result.scanned == 2 and result.duplicates == 1 and len(result.groups) == 1
    assert len(result.groups[0].provenance) == 2
    assert result.groups[0].first_seen_at == min(seen)
    # Selecting only the later source still preserves the older cross-source discovery.
    async with database.sessions() as session:
        later_only = await ListingCatalog(session).scan(user, [source_ids[1]])
    assert later_only.groups[0].first_seen_at == min(seen)
    async with database.sessions() as session:
        assert not (await ListingCatalog(session).scan(uuid4(), source_ids)).groups
    async with database.sessions() as session:
        assert (await ListingService(session).page(user, 20, 0)).total == 2
