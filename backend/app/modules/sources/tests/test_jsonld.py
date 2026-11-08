"""Offline synthetic JobPosting fixtures, not real jobs or calibration labels."""

import json
import logging
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.sources.connectors import (
    AllowedRoute,
    CollectedResponse,
    CollectionAuthorization,
    CollectionLimits,
    ConnectorFailure,
    ConnectorQuery,
    ManualConnector,
    NormalizedListing,
)
from app.modules.sources.connectors.http_client import CollectionBudget
from app.modules.sources.connectors.jsonld import extract_job_postings, normalize_jsonld_page
from app.modules.sources.tests.test_policy import valid_evidence

DOCUMENT = "https://api.example.test/jobs/fixture"
OBSERVED = datetime(2026, 11, 8, 12, tzinfo=UTC)


def job(**updates: object) -> dict[str, object]:
    return {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "url": "/jobs/fixture",
        "title": "Développeur synthétique",
        "hiringOrganization": {"@type": "Organization", "name": "Entreprise fictive"},
        "description": "<p>Fixture seulement : français العربية.</p>",
        "datePosted": "2026-11-08T10:30:00+01:00",
        **updates,
    }


def script(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return '<script type="application/ld+json">' + encoded + "</script>"


def response(html: str, content_type: str = "text/html") -> CollectedResponse:
    return CollectedResponse(DOCUMENT, content_type, html.encode("utf-8"), OBSERVED)


def authorization() -> CollectionAuthorization:
    return CollectionAuthorization(
        uuid4(),
        uuid4(),
        True,
        "PERMITTED",
        valid_evidence(),
        (AllowedRoute("api.example.test", "/jobs"),),
    )


@pytest.mark.parametrize("wrapper", ["root", "array", "graph", "mainEntity", "listItem"])
def test_supported_shapes_and_types(wrapper: str) -> None:
    value: object = job(**{"@type": ["Thing", "https://schema.org/JobPosting"]})
    if wrapper == "array":
        value = [value]
    elif wrapper == "graph":
        value = {"@graph": [value]}
    elif wrapper == "mainEntity":
        value = {"mainEntity": value}
    elif wrapper == "listItem":
        value = {"itemListElement": [{"@type": "ListItem", "item": value}]}
    batch = extract_job_postings(response(script(value)))
    assert batch.status == "OK" and batch.matched == 1
    item = batch.items[0]
    assert item.title == "Développeur synthétique" and "العربية" in (item.description or "")
    assert item.company == "Entreprise fictive" and item.original_url == DOCUMENT
    assert item.published_at == datetime(2026, 11, 8, 9, 30, tzinfo=UTC)
    assert item.publication_precision == "INSTANT" and item.published_date is None
    assert (
        item.extractor_version == "jobposting-jsonld-v1"
        and len(item.source_payload_hash or "") == 64
    )


def test_local_graph_references_locations_and_no_inferred_visa_or_seniority() -> None:
    value = {
        "@graph": [
            {"@id": "#company", "@type": "Organization", "name": "Fictive SA"},
            job(
                hiringOrganization={"@id": "#company"},
                jobLocation=[
                    {
                        "@type": "Place",
                        "address": {
                            "addressCountry": {"name": "Tunisia"},
                            "addressLocality": "Tunis",
                            "addressRegion": "Tunis",
                        },
                    },
                    {
                        "@type": "Place",
                        "address": {"addressCountry": "France", "addressLocality": "Paris"},
                    },
                ],
                applicantLocationRequirements=[{"name": "France"}],
                jobLocationType="TELECOMMUTE",
                employmentType=["FULL_TIME", "CONTRACTOR"],
                skills=["Python", {"name": "Angular"}],
                identifier={"value": 123},
                experienceRequirements="Fixture : 2 ans explicitement demandés",
            ),
        ]
    }
    item = extract_job_postings(response(script(value))).items[0]
    assert item.company == "Fictive SA" and item.source_job_id == "123"
    assert [p.city for p in item.locations] == ["Tunis", "Paris"]
    assert item.locations[0].country == "Tunisia"
    assert item.applicant_locations == ["France"] and item.work_mode == "remote"
    assert item.employment_types == ["FULL_TIME", "CONTRACTOR"]
    assert item.skills == ["Python", "Angular"]
    assert item.experience_requirements == "Fixture : 2 ans explicitement demandés"
    assert "visa_status" not in item.model_dump() and "experience_level" not in item.model_dump()


@pytest.mark.parametrize(
    "value,precision,warning",
    [
        ("2026-11-08", "DATE", "PUBLICATION_TIME_UNKNOWN"),
        ("2026-11-08T10:30:00", "LOCAL_DATETIME", "PUBLICATION_TIMEZONE_UNKNOWN"),
        ("2026-02-30", "UNKNOWN", "PUBLICATION_INVALID"),
        ("hier", "UNKNOWN", "PUBLICATION_INVALID"),
        (None, "UNKNOWN", "PUBLICATION_UNKNOWN"),
    ],
)
def test_uncertain_dates_never_become_import_time_or_midnight(
    value: str | None, precision: str, warning: str
) -> None:
    item = extract_job_postings(response(script(job(datePosted=value)))).items[0]
    assert item.published_at is None and item.publication_precision == precision
    assert warning in item.warnings
    if precision in {"DATE", "LOCAL_DATETIME"}:
        assert item.published_date == date(2026, 11, 8)
    assert item.publication_raw == value


def test_description_is_plain_text_and_remote_context_is_never_resolved() -> None:
    content = job(
        description=(
            "<p>Safe fixture</p><script>PRIVATE_SCRIPT</script><style>PRIVATE_STYLE</style>"
            "<template><script>PRIVATE_TEMPLATE</script></template>"
            '<iframe src="http://127.0.0.1/secret"></iframe><img src="http://internal/secret">'
            "<p>End &amp; text</p>"
        ),
        **{"@context": "http://127.0.0.1/forbidden"},
    )
    item = extract_job_postings(response(script(content))).items[0]
    assert item.description == "Safe fixture\nEnd & text"
    assert "PRIVATE" not in item.description


@pytest.mark.parametrize(
    "target", ["javascript:secret", "http://example.test/job", "https://u:p@example.test/job"]
)
def test_unsafe_job_urls_are_rejected_without_leaking_raw_data(target: str) -> None:
    batch = extract_job_postings(response(script(job(url=target))))
    assert batch.status == "FAILED" and batch.items == [] and batch.invalid == 1
    assert batch.issues == ["JOB_INVALID"]
    assert target not in repr(batch)


def test_application_link_is_real_and_invalid_optional_link_is_reported() -> None:
    item = extract_job_postings(
        response(
            script(
                job(
                    potentialAction={
                        "@type": "ApplyAction",
                        "target": {"urlTemplate": "https://apply.example.test/fixture"},
                    }
                )
            )
        )
    ).items[0]
    assert item.application_url == "https://apply.example.test/fixture"
    item = extract_job_postings(response(script(job(applicationUrl="javascript:bad")))).items[0]
    assert item.application_url is None and "APPLICATION_URL_INVALID" in item.warnings
    item = extract_job_postings(response(script(job(directApply=True)))).items[0]
    assert item.application_url is None  # A boolean is not a separate destination URL.


def test_single_document_url_fallback_does_not_invent_urls_on_a_list_page() -> None:
    value = job()
    value.pop("url")
    item = extract_job_postings(response(script(value))).items[0]
    assert item.original_url == DOCUMENT and "URL_FROM_DOCUMENT" in item.warnings
    batch = extract_job_postings(response(script([value, value])))
    assert batch.items == [] and batch.invalid == 2


@pytest.mark.parametrize(
    "text,code",
    [
        ('{"@type":"JobPosting","title":"PRIVATE","title":"duplicate"}', "JSON_DUPLICATE_KEY"),
        ('{"@type":"JobPosting","number":NaN}', "JSON_INVALID_NUMBER"),
        ('{"@type": PRIVATE_SECRET}', "JSON_INVALID"),
        ("[" * 40 + "0" + "]" * 40, "JSON_DEPTH_LIMIT"),
        ("[" + "0," * 10001 + "0]", "JSON_NODE_LIMIT"),
    ],
)
def test_invalid_json_is_visible_and_other_valid_scripts_are_preserved(
    text: str, code: str
) -> None:
    batch = extract_job_postings(
        response('<script type="application/ld+json">' + text + "</script>" + script(job()))
    )
    assert batch.status == "PARTIAL" and len(batch.items) == 1 and code in batch.issues
    assert "PRIVATE" not in repr(batch)


def test_empty_is_explicit_and_page_reader_never_reports_false_empty_success() -> None:
    batch = extract_job_postings(response("<p>Fixture sans données structurées</p>"))
    assert batch.status == "EMPTY" and batch.issues == ["NO_JSONLD"]
    batch = extract_job_postings(response(script({"@type": "Organization", "name": "Fixture"})))
    assert batch.status == "EMPTY" and "NO_JOBPOSTINGS" in batch.issues
    with pytest.raises(ConnectorFailure) as error:
        normalize_jsonld_page(
            response("empty"),
            ConnectorQuery(),
            CollectionBudget(CollectionLimits()),
            authorization(),
        )
    assert error.value.code == "PARSE_ERROR"


def test_limits_truncation_and_approved_pagination() -> None:
    html = '<link rel="next" href="/jobs/page2">' + script(
        [job(url="/jobs/one"), job(url="/jobs/two"), job(url="/jobs/three")]
    )
    budget = CollectionBudget(CollectionLimits(max_results=2))
    page = normalize_jsonld_page(response(html), ConnectorQuery(limit=2), budget, authorization())
    assert len(page.items) == 2 and page.truncated and page.next_cursor is None
    assert budget.results == 2  # Do not skip the third item by advertising page 2.
    assert page.matched_count == 3 and page.partial
    with pytest.raises(ConnectorFailure) as error:
        normalize_jsonld_page(response(html), ConnectorQuery(), budget, authorization())
    assert error.value.code == "RESULT_LIMIT"
    budget = CollectionBudget(CollectionLimits())
    page = normalize_jsonld_page(response(html), ConnectorQuery(), budget, authorization())
    assert not page.truncated and page.next_cursor == "https://api.example.test/jobs/page2"


def test_pagination_scope_and_untrusted_html_base_are_respected() -> None:
    html = (
        '<base href="http://127.0.0.1/">'
        '<link rel="next" href="https://outside.example.test/jobs/page2">' + script(job())
    )
    page = normalize_jsonld_page(
        response(html), ConnectorQuery(), CollectionBudget(CollectionLimits()), authorization()
    )
    assert page.items[0].original_url == DOCUMENT and page.next_cursor is None and page.truncated
    assert "PAGINATION_NOT_PERMITTED" in page.warnings


@pytest.mark.parametrize("body", [b"\xff", b"x" * 2_097_153, ("<i>" * 20_001).encode()])
def test_body_encoding_size_and_markup_complexity_are_bounded(body: bytes) -> None:
    with pytest.raises(ConnectorFailure) as error:
        extract_job_postings(CollectedResponse(DOCUMENT, "text/html", body, OBSERVED))
    assert error.value.code == "PARSE_ERROR"


def test_external_scripts_and_excessive_script_count_are_reported() -> None:
    external = '<script type="application/ld+json" src="http://127.0.0.1/private"></script>'
    batch = extract_job_postings(response(external + script(job()) * 33))
    assert batch.status == "PARTIAL" and batch.truncated and len(batch.items) == 32
    assert "EXTERNAL_JSONLD_IGNORED" in batch.issues and "SCRIPT_LIMIT" in batch.issues


def test_direct_jsonld_and_context_definitions_are_not_confused_with_jobs() -> None:
    batch = extract_job_postings(response(json.dumps(job()), "application/ld+json"))
    assert batch.status == "OK" and len(batch.items) == 1
    batch = extract_job_postings(response(script({"@context": {"fake": job()}})))
    assert batch.items == []
    with pytest.raises(ConnectorFailure):
        extract_job_postings(response(script(job()), "application/pdf"))


def test_output_provenance_and_errors_do_not_log_content(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    first = extract_job_postings(response(script(job(title="SYNTHETIC_PRIVATE_TITLE"))))
    second = extract_job_postings(response(script(job(title="SYNTHETIC_PRIVATE_TITLE"))))
    assert first.items[0].source_payload_hash == second.items[0].source_payload_hash
    assert first.items[0].source_document_url == DOCUMENT
    assert "SYNTHETIC_PRIVATE_TITLE" not in repr(first)
    assert "SYNTHETIC_PRIVATE_TITLE" not in caplog.text


def test_manual_normalization_remains_compatible() -> None:
    item = ManualConnector().normalize({"original_url": DOCUMENT, "title": "Fixture"})
    assert item.title == "Fixture" and item.publication_precision == "UNKNOWN"


@pytest.mark.parametrize(
    "fields",
    [
        {"published_at": OBSERVED},
        {"published_at": datetime(2026, 11, 8), "publication_precision": "INSTANT"},
        {"publication_precision": "INSTANT"},
        {"publication_precision": "DATE"},
    ],
)
def test_date_precision_cannot_be_misrepresented(fields: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        NormalizedListing.model_validate({"original_url": DOCUMENT, **fields})


def test_ambiguous_references_and_pagination_are_reported() -> None:
    value = {
        "@graph": [
            {"@id": "#company", "name": "First fictive company"},
            {"@id": "#company", "name": "Other fictive company"},
            job(hiringOrganization={"@id": "#company"}),
        ]
    }
    html = '<link rel="next" href="/jobs/a"><link rel="next" href="/jobs/b">' + script(value)
    batch = extract_job_postings(response(html))
    assert batch.items[0].company is None
    assert batch.next_url is None and batch.status == "PARTIAL"
    assert {"REFERENCE_AMBIGUOUS", "PAGINATION_AMBIGUOUS"} <= set(batch.issues)


def test_scripts_field_limits_and_invalid_items_remain_visible() -> None:
    excessive = job(description="x" * 150001)
    html = script([excessive, job()])
    page = normalize_jsonld_page(
        response(html), ConnectorQuery(), CollectionBudget(CollectionLimits()), authorization()
    )
    assert page.partial and page.invalid_count == 1 and page.matched_count == 2
    assert len(page.items) == 1 and "JOB_INVALID" in page.warnings
    oversized_json = script({"value": "x" * 262145}) + script(job())
    batch = extract_job_postings(response(oversized_json))
    assert batch.status == "PARTIAL" and "JSON_SIZE_LIMIT" in batch.issues
