from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError

from app.modules.sources.connectors import ConnectorFailure, ConnectorQuery, ManualConnector
from app.modules.sources.policy import verified_automation
from app.modules.sources.schemas import SourceCreate
from app.shared.clock import utcnow
from app.shared.urls import canonical_url


def valid_evidence() -> dict[str, object]:
    now = utcnow().isoformat()
    return {
        "api_url": "https://api.example.test/jobs",
        "terms_url": "https://example.test/terms",
        "access_method": "public",
        "allowed_usage": "fixture",
        "rate_limit": "1/min",
        "reviewer": "test",
        "evidence": "fixture only",
        "robots_allowed": True,
        "access_confirmed": True,
        "robots_checked_at": now,
        "terms_reviewed_at": now,
    }


def test_complete_current_permission_required() -> None:
    evidence = valid_evidence()
    assert verified_automation("PERMITTED", evidence)
    assert not verified_automation("UNVERIFIED", evidence)
    assert not verified_automation("PERMITTED", {})
    evidence["robots_allowed"] = False
    assert not verified_automation("PERMITTED", evidence)


@pytest.mark.parametrize("key", ["robots_checked_at", "terms_reviewed_at"])
@pytest.mark.parametrize("offset", [-91, -90, 1])
def test_stale_and_future_reviews_never_authorize(key: str, offset: int) -> None:
    evidence = valid_evidence()
    evidence[key] = (utcnow() + timedelta(days=offset)).isoformat()
    assert not verified_automation("PERMITTED", evidence)


async def test_manual_connector_never_performs_automatic_collection() -> None:
    connector = ManualConnector()
    assert not connector.capabilities().automated
    assert await connector.health_check() == "MANUAL_ONLY"
    with pytest.raises(ConnectorFailure) as error:
        await connector.fetch(ConnectorQuery(keywords="Python"))
    assert error.value.code == "MANUAL_ONLY"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/",
        "javascript:alert(1)",
        "https://127.0.0.1/a",
        "https://127.0.0.1./a",
        "https://user:secret@example.com/a",
        "https://test.local/a",
        "https://example.com:8443/a",
    ],
)
def test_unsafe_source_urls_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        SourceCreate(name="test", homepage=url)


def test_url_normalization_keeps_job_identity_and_strips_tracking() -> None:
    result = canonical_url(
        "https://WWW.indeed.com/viewjob?utm_campaign=test&jk=123&from=search#detail"
    )
    assert urlsplit(result).hostname == "www.indeed.com"
    assert parse_qs(urlsplit(result).query) == {"jk": ["123"]}


def test_registry_has_no_implicit_automated_fallback() -> None:
    from app.modules.sources.connectors import connector_for

    assert not connector_for("LINK_ONLY").capabilities().automated
    with pytest.raises(ConnectorFailure) as error:
        connector_for("API")
    assert error.value.code == "UNAVAILABLE"
    with pytest.raises(ConnectorFailure) as parse_error:
        connector_for("MANUAL_IMPORT").normalize({"original_url": "javascript:secret"})
    assert parse_error.value.code == "PARSE_ERROR"
    assert "secret" not in str(parse_error.value)
