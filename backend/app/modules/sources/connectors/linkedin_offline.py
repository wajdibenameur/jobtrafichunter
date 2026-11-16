"""Synthetic-only LinkedIn feasibility prototype, never a production connector.

No LinkedIn endpoint, credentials, source permission or adapter registration lives
here. BeautifulSoup/JSON-LD normalization is reused from the existing extractor.
"""

from datetime import datetime

import httpx

from app.modules.sources.connectors.contracts import (
    CollectedResponse,
    ConnectorFailure,
    ConnectorPage,
    ConnectorQuery,
)
from app.modules.sources.connectors.http_client import retry_delay
from app.modules.sources.connectors.jsonld import extract_job_postings

FIXTURE_ORIGIN = "https://fixtures.example.test"


async def offline_page(
    query: ConnectorQuery,
    transport: httpx.MockTransport,
    *,
    observed_at: datetime,
) -> ConnectorPage:
    """Parse one mocked page; pagination and dates are fixture contracts only.

    Search/time parameters are forwarded for inspection by tests. Final filtering,
    persistence, deduplication and matching belong to the existing pipeline.
    """
    if type(transport) is not httpx.MockTransport:
        raise ConnectorFailure("OFFLINE_ONLY", "An explicit mock transport is required")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ConnectorFailure("CONFIGURATION", "An explicit observation timezone is required")
    cursor = query.cursor if query.cursor is not None else "0"
    if cursor not in {"0", "1"}:
        raise ConnectorFailure("CONFIGURATION", "Unknown fixture page cursor")
    try:
        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=5,
        ) as client:
            response = await client.get(
                f"{FIXTURE_ORIGIN}/pages/{cursor}",
                params={
                    "keywords": query.keywords,
                    "location": query.location,
                    "minutes": str(query.publication_minutes or ""),
                },
            )
    except httpx.TimeoutException:
        raise ConnectorFailure("TIMEOUT", "Offline fixture timed out") from None
    except httpx.HTTPError:
        raise ConnectorFailure("NETWORK_ERROR", "Offline fixture transport failed") from None
    if response.status_code in {401, 403}:
        raise ConnectorFailure(
            "AUTH" if response.status_code == 401 else "BLOCKED", "Offline fixture denied access"
        )
    if response.status_code == 429:
        raise ConnectorFailure(
            "RATE_LIMITED",
            "Offline fixture rate limit",
            retry_after=retry_delay(response.headers.get("retry-after")),
        )
    if 300 <= response.status_code < 400:
        raise ConnectorFailure("PROTOCOL_ERROR", "Offline fixture redirects are not followed")
    if response.status_code != 200:
        raise ConnectorFailure("HTTP_ERROR", "Offline fixture returned an unsuccessful status")
    batch = extract_job_postings(
        CollectedResponse(
            str(response.url),
            response.headers.get("content-type", ""),
            response.content,
            observed_at,
        ),
        limit=query.limit,
    )
    if not batch.items:
        raise ConnectorFailure("PARSE_ERROR", "No usable fixture JobPosting data")
    if batch.next_url not in {None, f"{FIXTURE_ORIGIN}/pages/1"} or (
        cursor == "1" and batch.next_url is not None
    ):
        raise ConnectorFailure("UNSAFE_URL", "Unexpected or repeated fixture pagination")
    warnings = list(
        dict.fromkeys(
            ["OFFLINE_FIXTURE", *batch.issues, *(w for item in batch.items for w in item.warnings)]
        )
    )
    return ConnectorPage(
        items=batch.items,
        next_cursor="1" if batch.next_url and not batch.truncated else None,
        truncated=batch.truncated,
        partial=batch.status == "PARTIAL",
        warnings=warnings[:100],
        matched_count=batch.matched,
        invalid_count=batch.invalid,
    )
