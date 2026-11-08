"""Bounded, GET-only collection transport. No provider is enabled by this module."""

import asyncio
import math
import random
import time
import zlib
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime
from uuid import UUID

import httpcore
import httpx

from app.modules.sources.connectors.access import AuthorizationProvider, CollectionAuthorization
from app.modules.sources.connectors.contracts import (
    CollectedResponse,
    CollectionLimits,
    ConnectorFailure,
)
from app.modules.sources.connectors.network import PinnedTransport, PublicNetworkBackend
from app.shared.clock import utcnow

Sleeper = Callable[[float], Awaitable[None]]


class CollectionBudget:
    """One execution budget; retries and redirects consume the same allowance."""

    def __init__(self, limits: CollectionLimits) -> None:
        self.limits = limits
        self.started = time.monotonic()
        self.requests = self.pages = self.results = self.wire_bytes = self.body_bytes = 0

    def remaining(self) -> float:
        seconds = self.limits.duration_seconds - (time.monotonic() - self.started)
        if seconds <= 0:
            raise ConnectorFailure("DEADLINE", "Collection deadline reached")
        return seconds

    def reserve_page(self) -> None:
        self.remaining()
        if self.pages >= self.limits.max_pages:
            raise ConnectorFailure("PAGE_LIMIT", "Collection page limit reached")
        self.pages += 1

    def reserve_request(self) -> None:
        self.remaining()
        if self.requests >= self.limits.max_requests:
            raise ConnectorFailure("REQUEST_LIMIT", "Collection request limit reached")
        self.requests += 1

    def record_results(self, count: int) -> None:
        # Adapters must call this before yielding a normalized page (lot 3).
        if count < 0 or self.results + count > self.limits.max_results:
            raise ConnectorFailure("RESULT_LIMIT", "Collection result limit reached")
        self.results += count


@dataclass
class _SourceSlot:
    lock: asyncio.Lock
    next_at: float = 0
    interval: float = 0
    last_at: float | None = None


class CollectionCoordinator:
    """Share one instance in the worker; source throttles also cover concurrent runs."""

    def __init__(self, max_concurrency: int = 4) -> None:
        if not 1 <= max_concurrency <= 4:
            raise ValueError("Concurrency must be between 1 and 4")
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._sources: dict[UUID, _SourceSlot] = {}

    async def wait_turn(self, source: UUID, interval: float, sleep: Sleeper) -> None:
        slot = self._sources.setdefault(source, _SourceSlot(asyncio.Lock()))
        async with slot.lock:
            slot.interval = max(interval, slot.interval)
            if slot.last_at is not None:
                slot.next_at = max(slot.next_at, slot.last_at + slot.interval)
            # Windows timers may wake a little early. Also recheck cooldowns
            # extended by a 429 received while this task was sleeping.
            while (delay := slot.next_at - time.monotonic()) > 0:
                await sleep(delay)
            slot.last_at = time.monotonic()
            slot.next_at = slot.last_at + slot.interval

    def defer(self, source: UUID, delay: float) -> None:
        slot = self._sources.setdefault(source, _SourceSlot(asyncio.Lock()))
        slot.next_at = max(slot.next_at, time.monotonic() + delay)


def retry_delay(value: str | None) -> float | None:
    if not value or len(value) > 100:
        return None
    try:
        delay = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                return None
            delay = (date.astimezone(UTC) - utcnow()).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return None
    return float(min(86400, max(0, delay))) if math.isfinite(delay) else None


class CollectionHttpClient:
    def __init__(
        self,
        authorization: AuthorizationProvider,
        limits: CollectionLimits,
        coordinator: CollectionCoordinator,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleeper = asyncio.sleep,
    ) -> None:
        self._authorization, self._coordinator, self._sleep = authorization, coordinator, sleep
        self.limits, self.budget = limits, CollectionBudget(limits)
        self._identity: tuple[UUID, UUID] | None = None
        self._target: ContextVar[httpx.URL | None] = ContextVar("collection_target", default=None)
        self._transport = transport or PinnedTransport(PublicNetworkBackend(self._guard_host))

    async def _authorize(self, value: str) -> tuple[CollectionAuthorization, httpx.URL]:
        auth = await self._authorization()  # Fresh server-side state; no user-supplied boolean.
        auth.require()
        identity = (auth.owner_id, auth.source_id)
        if self._identity is not None and identity != self._identity:
            raise ConnectorFailure("NOT_PERMITTED", "Collection identity changed")
        self._identity = identity
        return auth, auth.check_url(value)

    async def _guard_host(self, host: str) -> None:
        target = self._target.get()
        if target is None or target.host != host:
            raise ConnectorFailure("UNSAFE_URL", "Connection is outside the active request")
        await self._authorize(str(target))

    async def get(self, value: str) -> CollectedResponse:
        try:
            async with asyncio.timeout(self.budget.remaining()):
                await self._authorize(value)
                self.budget.reserve_page()
                return await self._get(value)
        except (TimeoutError, httpx.TimeoutException, httpcore.TimeoutException):
            raise ConnectorFailure("TIMEOUT", "Collection request timed out") from None

    async def _get(self, value: str) -> CollectedResponse:
        redirects = attempts = 0
        current = value
        while True:
            auth, url = await self._authorize(current)
            # Hold the concurrency slot while waiting for the source's next turn,
            # so no request accumulates a stale rate reservation behind the pool.
            async with self._coordinator.semaphore:
                await self._coordinator.wait_turn(
                    auth.source_id, self.limits.min_interval_seconds, self._sleep
                )
                _, url = await self._authorize(str(url))
                self.budget.reserve_request()
                try:
                    outcome = await self._request(url)
                except (httpx.NetworkError, httpcore.NetworkError, OSError):
                    outcome = ("retry", None)
                except (httpx.ProtocolError, httpcore.ProtocolError, httpx.DecodingError):
                    raise ConnectorFailure(
                        "PROTOCOL_ERROR", "Invalid collection response"
                    ) from None
                if isinstance(outcome, tuple) and isinstance(outcome[1], float):
                    self._coordinator.defer(auth.source_id, outcome[1])
            if isinstance(outcome, CollectedResponse):
                return outcome
            action, detail = outcome
            if action == "redirect":
                if redirects >= self.limits.max_redirects:
                    raise ConnectorFailure("REDIRECT_LIMIT", "Collection redirect limit reached")
                redirects += 1
                assert isinstance(detail, str)
                current = detail
                continue
            attempts += 1
            delay = detail if isinstance(detail, float) else 2 ** (attempts - 1) + random.random()
            if attempts >= self.limits.max_attempts or delay >= self.budget.remaining():
                raise ConnectorFailure(
                    "RATE_LIMITED" if detail is not None else "UNAVAILABLE",
                    "Collection retry limit reached",
                    retry_after=detail if isinstance(detail, float) else None,
                )
            await self._sleep(delay)

    async def _request(self, url: httpx.URL) -> CollectedResponse | tuple[str, str | float | None]:
        timeout = min(self.limits.timeout_seconds, self.budget.remaining())
        # Direct transport calls avoid HTTPX request logging (which includes the URL),
        # client cookie persistence and proxy/environment configuration altogether.
        request = httpx.Request(
            "GET",
            url,
            headers={
                "User-Agent": "JobHunterAI/0.1 (authorized job sources only)",
                "Accept": "application/json, application/rss+xml, text/html, text/plain",
                "Accept-Encoding": "identity",
            },
            extensions={"timeout": {key: timeout for key in ("connect", "read", "write", "pool")}},
        )
        token = self._target.set(url)
        response = None
        try:
            async with asyncio.timeout(timeout):
                response = await self._transport.handle_async_request(request)
                status = response.status_code
                if status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location or len(location) > 4096:
                        raise ConnectorFailure("PROTOCOL_ERROR", "Invalid collection redirect")
                    try:
                        target = str(url.join(location))
                    except (ValueError, httpx.InvalidURL):
                        raise ConnectorFailure(
                            "UNSAFE_URL", "Invalid redirect destination"
                        ) from None
                    await self._authorize(target)
                    return "redirect", target
                if status in {401, 403}:
                    raise ConnectorFailure(
                        "AUTH" if status == 401 else "BLOCKED", "Source denied access"
                    )
                if status in {429, 502, 503, 504}:
                    delay = retry_delay(response.headers.get("retry-after"))
                    if status == 429 and delay is None:
                        delay = max(self.limits.min_interval_seconds, 1)
                    return "retry", delay
                if status != 200:
                    raise ConnectorFailure("HTTP_ERROR", "Source returned an unsuccessful response")
                body = await self._read(response)
                return CollectedResponse(
                    str(url), response.headers.get("content-type", ""), body, utcnow()
                )
        finally:
            self._target.reset(token)
            if response is not None:
                await response.aclose()

    async def _read(self, response: httpx.Response) -> bytes:
        encoding = response.headers.get("content-encoding", "identity").strip().lower()
        if encoding not in {"identity", "gzip"}:
            raise ConnectorFailure("UNSUPPORTED_ENCODING", "Unsupported response compression")
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
        body = bytearray()
        wire = 0
        try:
            async for chunk in response.aiter_raw():
                wire += len(chunk)
                self.budget.wire_bytes += len(chunk)
                if (
                    wire > self.limits.max_wire_bytes
                    or self.budget.wire_bytes > self.limits.max_total_bytes
                ):
                    raise ConnectorFailure("SIZE_LIMIT", "Collection download limit reached")
                room = min(
                    self.limits.max_body_bytes - len(body),
                    self.limits.max_total_bytes - self.budget.body_bytes,
                )
                part = decoder.decompress(chunk, room + 1) if decoder else chunk
                self.budget.body_bytes += len(part)
                if len(part) > room:
                    raise ConnectorFailure("SIZE_LIMIT", "Collection decoded size limit reached")
                body.extend(part)
            if decoder and (not decoder.eof or decoder.unused_data):
                raise ConnectorFailure("PROTOCOL_ERROR", "Invalid compressed collection response")
        except zlib.error:
            raise ConnectorFailure(
                "PROTOCOL_ERROR", "Invalid compressed collection response"
            ) from None
        return bytes(body)

    async def aclose(self) -> None:
        await self._transport.aclose()
