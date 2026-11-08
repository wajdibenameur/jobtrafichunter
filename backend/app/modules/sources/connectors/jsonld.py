"""Bounded, offline JobPosting extraction. This module never fetches a URL."""

import hashlib
import json
import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from typing import Literal, NoReturn
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.filter import SoupStrainer
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.modules.sources.connectors.access import CollectionAuthorization
from app.modules.sources.connectors.contracts import (
    CollectedResponse,
    ConnectorFailure,
    ConnectorPage,
    ConnectorQuery,
    NormalizedListing,
    NormalizedLocation,
)
from app.modules.sources.connectors.http_client import CollectionBudget
from app.shared.urls import public_https_url

VERSION = "jobposting-jsonld-v1"
MAX_HTML_BYTES = 2_097_152
MAX_SCRIPT_BYTES = 262_144
MAX_JSON_BYTES = 524_288
MAX_NODES = 10_000
MAX_DEPTH = 32
MAX_SCRIPTS = 32


class ExtractionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    status: Literal["OK", "PARTIAL", "EMPTY", "FAILED"]
    items: list[NormalizedListing] = Field(default_factory=list, repr=False)
    matched: int = 0
    invalid: int = 0
    issues: list[str] = Field(default_factory=list)
    truncated: bool = False
    next_url: str | None = Field(default=None, repr=False)


class _InvalidData(ValueError):
    pass


class _HtmlBudget(HTMLParser):
    def __init__(self, maximum: int) -> None:
        super().__init__(convert_charrefs=False)
        self.count, self.maximum = 0, maximum

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.count += 1
        if self.count > self.maximum:
            raise _InvalidData("HTML_COMPLEXITY_LIMIT")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidData("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise _InvalidData("JSON_INVALID_NUMBER")


def _json_depth(text: str) -> None:
    depth = 0
    quoted = escaped = False
    for char in text:
        if escaped:
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted and char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise _InvalidData("JSON_DEPTH_LIMIT")
        elif not quoted and char in "]}":
            depth -= 1


def _nodes(root: object) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    pending = [root]
    count = 0
    while pending:
        value = pending.pop()
        count += 1
        if count > MAX_NODES:
            raise _InvalidData("JSON_NODE_LIMIT")
        if isinstance(value, dict):
            result.append(value)
            # @context definitions describe the vocabulary, not job records.
            pending.extend(v for k, v in reversed(list(value.items())) if k != "@context")
        elif isinstance(value, list):
            pending.extend(reversed(value))
    return result


def _text(value: object, maximum: int) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) > maximum or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise _InvalidData("FIELD_LIMIT")
    return value or None


def _types(value: object) -> list[str]:
    return (
        [value]
        if isinstance(value, str)
        else ([item for item in value if isinstance(item, str)] if isinstance(value, list) else [])
    )


def _typed(value: dict[str, object], name: str) -> bool:
    return any(
        t in {name, f"https://schema.org/{name}", f"http://schema.org/{name}"}
        for t in _types(value.get("@type"))
    )


def _resolve(value: object, index: dict[str, dict[str, object]]) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    identifier = value.get("@id")
    if len(value) == 1 and isinstance(identifier, str):
        return index.get(identifier, {})
    return value


def _labels(value: object, maximum: int, count: int) -> list[str]:
    values = value if isinstance(value, list) else [value]
    if len(values) > count:
        raise _InvalidData("FIELD_LIMIT")
    result: list[str] = []
    for item in values:
        label = _text(item.get("name") if isinstance(item, dict) else item, maximum)
        if label and label not in result:
            result.append(label)
    return result


def _link(value: object, document: str) -> str | None:
    text = _text(value, 4096)
    if not text:
        return None
    if any(c in text for c in "{}"):
        raise _InvalidData("UNSAFE_URL")
    try:
        return public_https_url(urljoin(document, text))
    except ValueError:
        raise _InvalidData("UNSAFE_URL") from None


def _description(value: object) -> str | None:
    text = _text(value, 150_000)
    if text is None:
        return None
    _HtmlBudget(2000).feed(text)
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all(
        ["script", "style", "iframe", "object", "svg", "template", "noscript"]
    ):
        if tag.parent is not None:
            tag.decompose()
    return _text(soup.get_text("\n", strip=True), 50_000)


def _publication(raw: object, warnings: list[str]) -> dict[str, object]:
    value = _text(raw, 128)
    if not value:
        warnings.append("PUBLICATION_UNKNOWN")
        return {}
    result: dict[str, object] = {"publication_raw": value}
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            result.update(published_date=date.fromisoformat(value), publication_precision="DATE")
            warnings.append("PUBLICATION_TIME_UNKNOWN")
        elif re.match(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}", value):
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if instant.tzinfo is None or instant.utcoffset() is None:
                result.update(published_date=instant.date(), publication_precision="LOCAL_DATETIME")
                warnings.append("PUBLICATION_TIMEZONE_UNKNOWN")
            else:
                result.update(published_at=instant.astimezone(UTC), publication_precision="INSTANT")
        else:
            raise ValueError
    except ValueError:
        warnings.append("PUBLICATION_INVALID")
    return result


def _locations(value: object, index: dict[str, dict[str, object]]) -> list[NormalizedLocation]:
    values = value if isinstance(value, list) else [value]
    if len(values) > 30:
        raise _InvalidData("FIELD_LIMIT")
    result: list[NormalizedLocation] = []
    for item in values:
        place = _resolve(item, index)
        address = _resolve(place.get("address"), index)
        location = NormalizedLocation(
            country=next(iter(_labels(address.get("addressCountry"), 100, 1)), None),
            city=_text(address.get("addressLocality"), 100),
            region=_text(address.get("addressRegion"), 100),
            label=_text(place.get("name") if place else item, 200),
        )
        if any(location.model_dump().values()) and location not in result:
            result.append(location)
    return result


def _normalize(
    node: dict[str, object], document: str, index: dict[str, dict[str, object]], single: bool
) -> NormalizedListing:
    warnings: list[str] = []
    url = _link(node.get("url"), document)
    if not url:
        identifier = node.get("@id")
        # A fragment is a graph identifier, not a distinct job URL.
        if (
            isinstance(identifier, str)
            and identifier.startswith("https://")
            and "#" not in identifier
        ):
            url = _link(identifier, document)
        elif single:
            url = document
            warnings.append("URL_FROM_DOCUMENT")
        else:
            raise _InvalidData("JOB_URL_MISSING")
    organization = _resolve(node.get("hiringOrganization"), index)
    identifier = node.get("identifier")
    identifier = identifier.get("value") if isinstance(identifier, dict) else identifier
    if isinstance(identifier, int) and not isinstance(identifier, bool):
        identifier = str(identifier)
    source_id = _text(identifier, 200)
    application = node.get("applicationUrl")
    actions = node.get("potentialAction")
    if application is None:
        for action in actions if isinstance(actions, list) else [actions]:
            action = _resolve(action, index)
            if _typed(action, "ApplyAction"):
                target = action.get("target")
                application = target.get("urlTemplate") if isinstance(target, dict) else target
                break
    try:
        apply_url = _link(application, document)
    except _InvalidData:
        apply_url = None
        warnings.append("APPLICATION_URL_INVALID")
    experience = node.get("experienceRequirements")
    if isinstance(experience, dict):
        experience = experience.get("description") or experience.get("name")
    fields: dict[str, object] = {
        "original_url": url,
        "application_url": apply_url,
        "title": _text(node.get("title"), 300),
        "company": _text(organization.get("name"), 200),
        "description": _description(node.get("description")),
        "source_job_id": source_id,
        "locations": _locations(node.get("jobLocation"), index),
        "applicant_locations": _labels(node.get("applicantLocationRequirements"), 1000, 30),
        "work_mode": "remote" if node.get("jobLocationType") == "TELECOMMUTE" else None,
        "employment_types": _labels(node.get("employmentType"), 100, 30),
        "skills": _labels(node.get("skills"), 1000, 100),
        "experience_requirements": _text(experience, 4000),
        "source_document_url": document,
        "source_payload_hash": hashlib.sha256(
            json.dumps(node, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()
        ).hexdigest(),
        "extractor_version": VERSION,
    }
    fields.update(_publication(node.get("datePosted"), warnings))
    for name in ("title", "company", "description"):
        if fields[name] is None:
            warnings.append(name.upper() + "_UNKNOWN")
    fields["warnings"] = warnings
    return NormalizedListing.model_validate(fields)


def extract_job_postings(response: CollectedResponse, *, limit: int = 500) -> ExtractionBatch:
    if not 1 <= limit <= 500:
        raise ConnectorFailure("CONFIGURATION", "Invalid extraction limit")
    media_type = response.content_type.split(";", 1)[0].strip().lower()
    if media_type not in {"text/html", "application/xhtml+xml", "application/ld+json"}:
        raise ConnectorFailure("PARSE_ERROR", "Unsupported structured response type")
    try:
        document = public_https_url(response.url)
        if len(response.body) > MAX_HTML_BYTES:
            raise _InvalidData("HTML_SIZE_LIMIT")
        html = response.body.decode("utf-8-sig", errors="strict")
        if media_type != "application/ld+json":
            _HtmlBudget(20_000).feed(html)
    except (ValueError, UnicodeError):
        raise ConnectorFailure("PARSE_ERROR", "Invalid or excessive structured document") from None
    soup = BeautifulSoup(
        html if media_type != "application/ld+json" else "",
        "html.parser",
        parse_only=SoupStrainer(["script", "link"]),
    )
    scripts: list[str] = [html] if media_type == "application/ld+json" else []
    issues: list[str] = []
    next_links: list[str] = []
    for tag in soup.find_all("script"):
        mime = str(tag.get("type", "")).lower().split(";", 1)[0].strip()
        if mime != "application/ld+json":
            continue
        if tag.get("src"):
            issues.append("EXTERNAL_JSONLD_IGNORED")
            continue
        scripts.append(str(tag.string or ""))
    for tag in soup.find_all("link"):
        if "next" in (tag.get("rel") or []):
            try:
                target = _link(tag.get("href"), document)
                if target and target not in next_links:
                    next_links.append(target)
            except _InvalidData:
                issues.append("PAGINATION_URL_INVALID")
    if len(next_links) > 1:
        issues.append("PAGINATION_AMBIGUOUS")
    nodes: list[dict[str, object]] = []
    total_bytes = 0
    truncated = len(scripts) > MAX_SCRIPTS
    if truncated:
        issues.append("SCRIPT_LIMIT")
    for text in scripts[:MAX_SCRIPTS]:
        total_bytes += len(text.encode("utf-8"))
        if len(text.encode("utf-8")) > MAX_SCRIPT_BYTES or total_bytes > MAX_JSON_BYTES:
            issues.append("JSON_SIZE_LIMIT")
            continue
        try:
            _json_depth(text)
            value: object = json.loads(
                text, object_pairs_hook=_unique, parse_constant=_reject_constant
            )
            parsed = _nodes(value)
            if len(nodes) + len(parsed) > MAX_NODES:
                raise _InvalidData("JSON_NODE_LIMIT")
            nodes.extend(parsed)
        except _InvalidData as error:
            issues.append(str(error))  # Fixed codes only; never raw parser error text.
        except (ValueError, RecursionError):
            issues.append("JSON_INVALID")
    index: dict[str, dict[str, object]] = {}
    ambiguous: set[str] = set()
    for node in nodes:
        identity = node.get("@id")
        if isinstance(identity, str) and len(node) > 1:
            if identity in index and index[identity] != node:
                ambiguous.add(identity)
            index[identity] = node
    for identity in ambiguous:
        index.pop(identity, None)
    if ambiguous:
        issues.append("REFERENCE_AMBIGUOUS")
    postings = [node for node in nodes if _typed(node, "JobPosting")]
    items: list[NormalizedListing] = []
    invalid = 0
    for node in postings:
        if len(items) >= limit:
            truncated = True
            break
        try:
            items.append(_normalize(node, document, index, len(postings) == 1))
        except (ValueError, ValidationError):
            invalid += 1
            issues.append("JOB_INVALID")
    if not scripts:
        issues.append("NO_JSONLD")
    elif not postings and not issues:
        issues.append("NO_JOBPOSTINGS")
    unique_issues = list(dict.fromkeys(issues))
    status: Literal["OK", "PARTIAL", "EMPTY", "FAILED"] = (
        "PARTIAL" if issues or invalid or truncated else "OK"
    )
    if not items:
        status = (
            "FAILED"
            if invalid or any(issue not in {"NO_JSONLD", "NO_JOBPOSTINGS"} for issue in issues)
            else "EMPTY"
        )
    return ExtractionBatch(
        status=status,
        items=items,
        matched=len(postings),
        invalid=invalid,
        issues=unique_issues,
        truncated=truncated,
        next_url=next_links[0] if len(next_links) == 1 else None,
    )


def normalize_jsonld_page(
    response: CollectedResponse,
    query: ConnectorQuery,
    budget: CollectionBudget,
    authorization: CollectionAuthorization,
) -> ConnectorPage:
    """Prepare a collected page; no fetching, persistence or provider activation."""
    authorization.require()
    authorization.check_url(response.url)
    budget.remaining()
    available = min(query.limit, budget.limits.max_results - budget.results)
    if available <= 0:
        raise ConnectorFailure("RESULT_LIMIT", "Collection result limit reached")
    batch = extract_job_postings(response, limit=available)
    budget.remaining()
    if not batch.items:
        raise ConnectorFailure("PARSE_ERROR", "No usable JobPosting data in the collected page")
    warnings = list(
        dict.fromkeys(batch.issues + [w for item in batch.items for w in item.warnings])
    )
    next_cursor = batch.next_url if not batch.truncated else None
    truncated = batch.truncated
    if next_cursor:
        try:
            authorization.check_url(next_cursor)
            if len(next_cursor) > 2048:
                raise ValueError
        except (ConnectorFailure, ValueError):
            next_cursor, truncated = None, True
            warnings.append("PAGINATION_NOT_PERMITTED")
    budget.record_results(len(batch.items))
    return ConnectorPage(
        items=batch.items,
        next_cursor=next_cursor,
        truncated=truncated,
        warnings=list(dict.fromkeys(warnings)),
        partial=batch.status == "PARTIAL" or truncated,
        matched_count=batch.matched,
        invalid_count=batch.invalid,
    )
