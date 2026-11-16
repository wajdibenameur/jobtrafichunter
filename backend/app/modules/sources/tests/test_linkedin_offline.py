"""Synthetic HTML only: no LinkedIn postings, permissions or network calls."""

import json
import socket
from datetime import UTC, datetime

import httpx
import pytest

from app.modules.sources.connectors import ConnectorFailure, ConnectorQuery, ConnectorRegistry
from app.modules.sources.connectors.linkedin_offline import FIXTURE_ORIGIN, offline_page

OBSERVED = datetime(2026, 11, 16, 12, tzinfo=UTC)


def document(
    *, next_url: str | None = None, date: str | None = "2026-11-16T10:30:00Z", count: int = 1
) -> str:
    jobs = []
    for index in range(count):
        job: dict[str, object] = {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "url": f"{FIXTURE_ORIGIN}/jobs/synthetic-{index}",
            "identifier": {"value": f"synthetic-{index}"},
            "title": f"DevOps SYNTHETIC {index}",
            "hiringOrganization": {"name": "SYNTHETIC employer"},
            "description": "<p>Fictional fixture only: Python and infrastructure.</p>",
            "jobLocation": {"address": {"addressCountry": "TN", "addressLocality": "Tunis"}},
        }
        if date is not None:
            job["datePosted"] = date
        jobs.append(job)
    link = f'<link rel="next" href="{next_url}">' if next_url is not None else ""
    return '<script type="application/ld+json">' + json.dumps(jobs) + "</script>" + link


def html_response(html: str) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html"}, text=html)


@pytest.mark.parametrize("minutes", [120, 360, 1440, 10080, 43200])
async def test_keywords_location_time_forwarded_and_existing_jsonld_normalization(
    minutes: int,
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return html_response(document(next_url="/pages/1"))

    page = await offline_page(
        ConnectorQuery(keywords="DevOps & Python", location="Tunisia", publication_minutes=minutes),
        httpx.MockTransport(handler),
        observed_at=OBSERVED,
    )
    assert calls[0].url.host == "fixtures.example.test"
    assert calls[0].url.params["keywords"] == "DevOps & Python"
    assert calls[0].url.params["location"] == "Tunisia"
    assert calls[0].url.params["minutes"] == str(minutes)
    assert page.next_cursor == "1" and page.matched_count == 1
    item = page.items[0]
    assert item.title == "DevOps SYNTHETIC 0" and item.locations[0].city == "Tunis"
    assert item.published_at == datetime(2026, 11, 16, 10, 30, tzinfo=UTC)
    assert item.extractor_version == "jobposting-jsonld-v1"
    assert "OFFLINE_FIXTURE" in page.warnings


async def test_two_pages_stop_without_a_second_deduplication_engine() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return html_response(
            document(next_url="/pages/1" if request.url.path.endswith("/0") else None)
        )

    transport = httpx.MockTransport(handler)
    first = await offline_page(ConnectorQuery(), transport, observed_at=OBSERVED)
    second = await offline_page(
        ConnectorQuery(cursor=first.next_cursor), transport, observed_at=OBSERVED
    )
    assert first.next_cursor == "1" and second.next_cursor is None
    assert first.items[0].original_url == second.items[0].original_url
    # Both observations survive; catalog ingestion owns deduplication and provenance.


@pytest.mark.parametrize(
    ("date", "precision"),
    [
        (None, "UNKNOWN"),
        ("2026-11-16", "DATE"),
        ("2026-11-16T10:30:00", "LOCAL_DATETIME"),
        ("10 hours ago", "UNKNOWN"),
    ],
)
async def test_incomplete_publication_never_becomes_a_precise_instant(
    date: str | None, precision: str
) -> None:
    page = await offline_page(
        ConnectorQuery(publication_minutes=120),
        httpx.MockTransport(lambda request: html_response(document(date=date))),
        observed_at=OBSERVED,
    )
    assert page.items[0].published_at is None
    assert page.items[0].publication_precision == precision
    assert page.items[0].warnings


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "AUTH"),
        (403, "BLOCKED"),
        (429, "RATE_LIMITED"),
        (302, "PROTOCOL_ERROR"),
        (503, "HTTP_ERROR"),
    ],
)
async def test_denials_and_limits_stop_without_retry_or_redirect(status: int, code: str) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status, headers={"retry-after": "60", "location": "https://www.linkedin.com/jobs/"}
        )

    with pytest.raises(ConnectorFailure) as error:
        await offline_page(
            ConnectorQuery(keywords="PRIVATE_QUERY"),
            httpx.MockTransport(handler),
            observed_at=OBSERVED,
        )
    assert error.value.code == code and calls == 1
    assert "PRIVATE_QUERY" not in str(error.value)
    if status == 429:
        assert error.value.retry_after == 60


@pytest.mark.parametrize("kind", ["timeout", "connection"])
async def test_transport_errors_are_sanitized(kind: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if kind == "timeout":
            raise httpx.ReadTimeout("PRIVATE_FIXTURE_PAYLOAD", request=request)
        raise httpx.ConnectError("PRIVATE_FIXTURE_PAYLOAD", request=request)

    with pytest.raises(ConnectorFailure) as error:
        await offline_page(ConnectorQuery(), httpx.MockTransport(handler), observed_at=OBSERVED)
    assert error.value.code == ("TIMEOUT" if kind == "timeout" else "NETWORK_ERROR")
    assert "PRIVATE_FIXTURE_PAYLOAD" not in str(error.value)


@pytest.mark.parametrize("url", ["https://www.linkedin.com/jobs/", "/pages/0", "/pages/2"])
async def test_unexpected_pagination_destinations_are_rejected(url: str) -> None:
    with pytest.raises(ConnectorFailure) as error:
        await offline_page(
            ConnectorQuery(),
            httpx.MockTransport(lambda request: html_response(document(next_url=url))),
            observed_at=OBSERVED,
        )
    assert error.value.code == "UNSAFE_URL"


async def test_repeated_last_page_is_rejected() -> None:
    with pytest.raises(ConnectorFailure, match="repeated"):
        await offline_page(
            ConnectorQuery(cursor="1"),
            httpx.MockTransport(lambda request: html_response(document(next_url="/pages/1"))),
            observed_at=OBSERVED,
        )


@pytest.mark.parametrize(
    "html", ["<html>No JSON-LD</html>", '<script type="application/ld+json">{invalid}</script>']
)
async def test_missing_or_malformed_structured_data_fails_closed(html: str) -> None:
    with pytest.raises(ConnectorFailure) as error:
        await offline_page(
            ConnectorQuery(),
            httpx.MockTransport(lambda request: html_response(html)),
            observed_at=OBSERVED,
        )
    assert error.value.code == "PARSE_ERROR"


async def test_result_limit_does_not_hide_truncation() -> None:
    page = await offline_page(
        ConnectorQuery(limit=1),
        httpx.MockTransport(lambda request: html_response(document(next_url="/pages/1", count=2))),
        observed_at=OBSERVED,
    )
    assert len(page.items) == 1 and page.truncated and page.partial
    assert page.next_cursor is None


@pytest.mark.parametrize("cursor", ["../real", "https://www.linkedin.com/jobs/", ""])
async def test_invalid_cursor_fails_before_transport(cursor: str) -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid cursor must not reach any transport")

    with pytest.raises(ConnectorFailure):
        await offline_page(
            ConnectorQuery(cursor=cursor), httpx.MockTransport(forbidden), observed_at=OBSERVED
        )


async def test_real_transport_is_refused() -> None:
    with pytest.raises(ConnectorFailure) as error:
        await offline_page(ConnectorQuery(), None, observed_at=OBSERVED)  # type: ignore[arg-type]
    assert error.value.code == "OFFLINE_ONLY"


async def test_offline_execution_does_not_open_a_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Offline fixture must not open a socket")

    monkeypatch.setattr(socket, "socket", forbidden)
    await offline_page(
        ConnectorQuery(),
        httpx.MockTransport(lambda request: html_response(document())),
        observed_at=OBSERVED,
    )


def test_no_production_adapter_is_available() -> None:
    with pytest.raises(ConnectorFailure) as error:
        ConnectorRegistry().resolve("LINKEDIN_OFFLINE")
    assert error.value.code == "NOT_PERMITTED"


async def test_naive_observation_fails_before_transport() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid observation must not reach transport")

    with pytest.raises(ConnectorFailure) as error:
        await offline_page(
            ConnectorQuery(), httpx.MockTransport(forbidden), observed_at=datetime(2026, 11, 16)
        )
    assert error.value.code == "CONFIGURATION"


@pytest.mark.parametrize("kind", ["oversized", "unsupported_media"])
async def test_existing_parser_bounds_are_preserved(kind: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if kind == "oversized":
            return html_response("x" * (2_097_152 + 1))
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"fixture")

    with pytest.raises(ConnectorFailure) as error:
        await offline_page(ConnectorQuery(), httpx.MockTransport(handler), observed_at=OBSERVED)
    assert error.value.code == "PARSE_ERROR"
