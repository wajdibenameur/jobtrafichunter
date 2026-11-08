"""Synthetic fixtures only: no DNS lookup, live provider, cookie or paid operation."""

import asyncio
import gzip
import logging
import ssl
from collections.abc import AsyncIterator, Callable, Coroutine, Iterable
from dataclasses import replace
from datetime import timedelta
from email.utils import format_datetime
from uuid import uuid4

import httpcore
import httpx
import pytest
from pydantic import ValidationError

from app.modules.sources.connectors import (
    AllowedRoute,
    CollectionAuthorization,
    CollectionLimits,
    ConnectorFailure,
    ConnectorPage,
    ConnectorQuery,
    ConnectorRegistry,
    ManualConnector,
)
from app.modules.sources.connectors.http_client import (
    CollectionBudget,
    CollectionCoordinator,
    CollectionHttpClient,
    retry_delay,
)
from app.modules.sources.connectors.network import PinnedTransport, PublicNetworkBackend
from app.modules.sources.tests.test_policy import valid_evidence
from app.shared.clock import utcnow

HOST = "api.example.test"
URL = f"https://{HOST}/jobs"
PUBLIC_IP = "93.184.216.34"


def access() -> CollectionAuthorization:
    return CollectionAuthorization(
        uuid4(), uuid4(), True, "PERMITTED", valid_evidence(), (AllowedRoute(HOST, "/jobs"),)
    )


def reply(
    content: bytes = b"fixture", status: int = 200, headers: dict[str, str] | None = None
) -> httpx.Response:
    return httpx.Response(status, headers=headers, stream=httpx.ByteStream(content))


async def no_wait(delay: float) -> None:
    pass


def client(
    handler: Callable[[httpx.Request], httpx.Response]
    | Callable[[httpx.Request], Coroutine[None, None, httpx.Response]],
    **limits: object,
) -> CollectionHttpClient:
    auth = access()

    async def provider() -> CollectionAuthorization:
        return auth

    return CollectionHttpClient(
        provider,
        CollectionLimits(min_interval_seconds=0.01, **limits),
        CollectionCoordinator(),
        transport=httpx.MockTransport(handler),
        sleep=no_wait,
    )


@pytest.mark.parametrize("state", ["disabled", "unverified", "expired", "no_routes"])
async def test_authorization_rejected_before_any_network(state: str) -> None:
    auth = access()
    if state == "disabled":
        auth = replace(auth, enabled=False)
    elif state == "unverified":
        auth = replace(auth, legal_status="UNVERIFIED")
    elif state == "no_routes":
        auth = replace(auth, routes=())
    else:
        evidence = dict(auth.verification)
        evidence["terms_reviewed_at"] = (utcnow() - timedelta(days=90)).isoformat()
        auth = replace(auth, verification=evidence)

    async def provider() -> CollectionAuthorization:
        return auth

    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("No network must occur")

    http = CollectionHttpClient(
        provider,
        CollectionLimits(),
        CollectionCoordinator(),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ConnectorFailure, match="authorization") as error:
        await http.get(URL)
    assert error.value.code == "NOT_PERMITTED" and http.budget.requests == 0
    await http.aclose()


@pytest.mark.parametrize(
    "target",
    [
        "http://api.example.test/jobs",
        "https://api.example.test.evil.test/jobs",
        "https://api.example.test/admin",
        "https://api.example.test/jobs-extra",
        "https://api.example.test/jobs/%2e%2e/admin",
        "https://api.example.test/jobs/%252e%252e/admin",
        "https://user:secret@api.example.test/jobs",
        "https://127.0.0.1/jobs",
        "https://api.example.test:8443/jobs",
        "https://api.example.test/jobs#fragment",
    ],
)
async def test_route_and_redirect_targets_cannot_escape_approved_scope(target: str) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return reply(status=302, headers={"location": target})

    http = client(handler)
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "UNSAFE_URL" and len(calls) == 1
    assert "secret" not in str(error.value)
    await http.aclose()


async def test_safe_redirect_no_cookies_auth_or_logging(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert "cookie" not in request.headers and "authorization" not in request.headers
        if len(requests) == 1:
            return reply(
                status=302, headers={"location": "/jobs/page2", "set-cookie": "token=PRIVATE"}
            )
        return reply(b"SYNTHETIC_PRIVATE_BODY", headers={"content-type": "application/json"})

    http = client(handler)
    response = await http.get(URL + "?token=SYNTHETIC_SECRET")
    assert response.url == URL + "/page2" and response.body == b"SYNTHETIC_PRIVATE_BODY"
    assert http.budget.requests == 2 and http.budget.pages == 1
    assert "SYNTHETIC_SECRET" not in caplog.text and "SYNTHETIC_PRIVATE_BODY" not in caplog.text
    assert "SYNTHETIC_PRIVATE_BODY" not in repr(response)
    await http.aclose()


@pytest.mark.parametrize("status,code", [(401, "AUTH"), (403, "BLOCKED"), (404, "HTTP_ERROR")])
async def test_permanent_errors_never_retry(status: int, code: str) -> None:
    http = client(lambda request: reply(b"private error", status=status))
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == code and http.budget.requests == 1
    assert "private" not in str(error.value)
    await http.aclose()


async def test_retry_after_and_global_request_budget() -> None:
    delays = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return reply(status=429, headers={"retry-after": "2"}) if count == 1 else reply()

    http = client(handler, max_requests=2)
    http._sleep = sleep
    assert (await http.get(URL)).body == b"fixture"
    assert 2 in delays
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "REQUEST_LIMIT" and count == 2
    await http.aclose()


async def test_quota_wait_that_cannot_fit_deadline_surfaces_without_retry() -> None:
    http = client(lambda request: reply(status=429, headers={"retry-after": "86400"}))
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "RATE_LIMITED" and error.value.retry_after == 86400
    assert http.budget.requests == 1
    await http.aclose()


async def test_retry_backoff_is_bounded_and_never_copies_exception_arguments() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("SYNTHETIC_SECRET", request=request)

    http = client(fail)
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "UNAVAILABLE" and http.budget.requests == 3
    assert "SYNTHETIC_SECRET" not in str(error.value)
    await http.aclose()


async def test_revoke_permission_while_waiting_prevents_the_next_request() -> None:
    auth = access()
    calls = 0

    async def provider() -> CollectionAuthorization:
        return auth

    async def revoke(delay: float) -> None:
        nonlocal auth
        auth = replace(auth, enabled=False)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return reply(status=503)

    http = CollectionHttpClient(
        provider,
        CollectionLimits(),
        CollectionCoordinator(),
        transport=httpx.MockTransport(handler),
        sleep=revoke,
    )
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "NOT_PERMITTED" and calls == 1
    await http.aclose()


@pytest.mark.parametrize("compressed", [False, True])
async def test_bounded_stream_and_gzip_bomb_are_rejected(compressed: bool) -> None:
    content = b"x" * 10000
    data = gzip.compress(content) if compressed else content
    headers = {"content-encoding": "gzip"} if compressed else {}
    http = client(lambda request: reply(data, headers=headers), max_body_bytes=64)
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "SIZE_LIMIT"
    # Bounded gzip decoding never allocates the entire expanded body.
    assert not compressed or http.budget.body_bytes == 65
    await http.aclose()


@pytest.mark.parametrize(
    "encoding,data,code",
    [
        ("gzip", gzip.compress(b"ok"), None),
        ("gzip", gzip.compress(b"ok")[:-2], "PROTOCOL_ERROR"),
        ("gzip", gzip.compress(b"ok") + gzip.compress(b"extra"), "PROTOCOL_ERROR"),
        ("gzip", b"invalid", "PROTOCOL_ERROR"),
        ("br", b"anything", "UNSUPPORTED_ENCODING"),
    ],
)
async def test_supported_compression_is_complete_and_unambiguous(
    encoding: str, data: bytes, code: str | None
) -> None:
    http = client(lambda request: reply(data, headers={"content-encoding": encoding}))
    if code:
        with pytest.raises(ConnectorFailure) as error:
            await http.get(URL)
        assert error.value.code == code
    else:
        assert (await http.get(URL)).body == b"ok"
    await http.aclose()


async def test_cancellation_and_deadline_close_the_stream() -> None:
    started, closed = asyncio.Event(), asyncio.Event()

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            started.set()
            await asyncio.Event().wait()
            yield b"never"

        async def aclose(self) -> None:
            closed.set()

    http = client(lambda request: httpx.Response(200, stream=Stream()))
    task = asyncio.create_task(http.get(URL))
    await asyncio.wait_for(started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()
    await http.aclose()

    closed.clear()
    http = client(lambda request: httpx.Response(200, stream=Stream()), duration_seconds=0.02)
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "TIMEOUT" and closed.is_set()
    await http.aclose()


async def test_source_throttling_is_shared_and_concurrency_is_bounded() -> None:
    coordinator = CollectionCoordinator(max_concurrency=1)
    auth = access()
    starts = []

    async def provider() -> CollectionAuthorization:
        return auth

    async def handler(request: httpx.Request) -> httpx.Response:
        starts.append(asyncio.get_running_loop().time())
        return reply()

    clients = [
        CollectionHttpClient(
            provider,
            CollectionLimits(min_interval_seconds=0.025),
            coordinator,
            transport=httpx.MockTransport(handler),
        )
        for _ in range(3)
    ]
    await asyncio.gather(*(http.get(URL) for http in clients))
    assert all(b - a >= 0.02 for a, b in zip(starts, starts[1:], strict=False))
    for http in clients:
        await http.aclose()


def test_limits_results_dates_and_registry_are_fail_closed() -> None:
    budget = CollectionBudget(CollectionLimits(max_results=1, max_pages=1))
    budget.record_results(1)
    with pytest.raises(ConnectorFailure, match="result limit"):
        budget.record_results(1)
    budget.reserve_page()
    with pytest.raises(ConnectorFailure, match="page limit"):
        budget.reserve_page()
    for value in (0, 501):
        with pytest.raises(ValidationError):
            ConnectorQuery(limit=value)
    assert ConnectorQuery().limit == 10 and ConnectorPage().items == []
    assert retry_delay("nan") is None and retry_delay("inf") is None
    assert retry_delay("not a date") is None
    delay = retry_delay(format_datetime(utcnow() + timedelta(seconds=5)))
    assert delay is not None and 0 <= delay <= 5
    registry = ConnectorRegistry()
    assert not registry.resolve("LINK_ONLY").capabilities().automated
    registry.register("SYNTHETIC", ManualConnector)
    with pytest.raises(ConnectorFailure) as error:
        registry.resolve("SYNTHETIC")
    assert error.value.code == "NOT_PERMITTED"
    assert isinstance(registry.resolve("SYNTHETIC", access()), ManualConnector)
    with pytest.raises(ConnectorFailure):
        registry.register("LINK_ONLY", ManualConnector)
    with pytest.raises(ConnectorFailure):
        registry.resolve("API", access())


@pytest.mark.parametrize(
    "addresses",
    [
        ["127.0.0.1"],
        ["10.0.0.1"],
        ["169.254.169.254"],
        ["::1"],
        ["fc00::1"],
        ["::ffff:127.0.0.1"],
        ["2002:7f00:1::"],
        ["224.0.0.1"],
        [PUBLIC_IP, "192.168.1.1"],
        [],
    ],
)
async def test_network_rejects_private_mixed_and_transition_addresses(addresses: list[str]) -> None:
    async def guard(host: str) -> None:
        assert host == HOST

    async def resolver(host: str) -> list[str]:
        return addresses

    class NoConnect(httpcore.AsyncNetworkBackend):
        async def connect_tcp(self, *args: object, **kwargs: object) -> httpcore.AsyncNetworkStream:
            pytest.fail("An unsafe DNS result must never connect")

    backend = PublicNetworkBackend(guard, resolver=resolver, delegate=NoConnect())
    with pytest.raises(ConnectorFailure):
        await backend.connect_tcp(HOST, 443, timeout=1)


async def test_pinned_connection_uses_validated_ip_original_host_and_tls_verification() -> None:
    auth = access()
    connected, sent, tls_names = [], [], []

    async def provider() -> CollectionAuthorization:
        return auth

    async def resolver(host: str) -> list[str]:
        return [PUBLIC_IP]

    async def guard(host: str) -> None:
        await http._guard_host(host)

    class Stream(httpcore.AsyncMockStream):
        async def write(
            self,
            buffer: bytes,
            timeout: float | None = None,  # noqa: ASYNC109 - override
        ) -> None:
            sent.append(buffer)

        async def start_tls(
            self,
            ssl_context: ssl.SSLContext,
            server_hostname: str | None = None,
            timeout: float | None = None,  # noqa: ASYNC109 - override
        ) -> httpcore.AsyncNetworkStream:
            assert ssl_context.check_hostname and ssl_context.verify_mode == ssl.CERT_REQUIRED
            tls_names.append(server_hostname)
            return self

        def get_extra_info(self, info: str) -> object:
            return (PUBLIC_IP, 443) if info == "server_addr" else super().get_extra_info(info)

    class Backend(httpcore.AsyncNetworkBackend):
        async def connect_tcp(
            self,
            host: str,
            port: int,
            timeout: float | None = None,  # noqa: ASYNC109 - override
            local_address: str | None = None,
            socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
        ) -> httpcore.AsyncNetworkStream:
            connected.append((host, port))
            return Stream([b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"])

    backend = PublicNetworkBackend(guard, resolver=resolver, delegate=Backend())
    http = CollectionHttpClient(
        provider, CollectionLimits(), CollectionCoordinator(), transport=PinnedTransport(backend)
    )
    assert (await http.get(URL)).body == b"ok"
    assert connected == [(PUBLIC_IP, 443)] and tls_names == [HOST]
    assert f"Host: {HOST}".encode() in b"".join(sent)
    await http.aclose()


@pytest.mark.parametrize("mode", ["revoked_dns", "wrong_peer", "revoked_connect"])
async def test_dns_and_connection_races_fail_closed_and_close_existing_stream(mode: str) -> None:
    permitted = True
    connected = []
    stream = None

    async def guard(host: str) -> None:
        if not permitted:
            raise ConnectorFailure("NOT_PERMITTED", "Authorization revoked")

    async def resolver(host: str) -> list[str]:
        nonlocal permitted
        if mode == "revoked_dns":
            permitted = False
        return [PUBLIC_IP]

    class Stream(httpcore.AsyncMockStream):
        def get_extra_info(self, info: str) -> object:
            peer = "127.0.0.1" if mode == "wrong_peer" else PUBLIC_IP
            return (peer, 443) if info == "server_addr" else None

    class Backend(httpcore.AsyncNetworkBackend):
        async def connect_tcp(
            self,
            host: str,
            port: int,
            timeout: float | None = None,  # noqa: ASYNC109 - override
            local_address: str | None = None,
            socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
        ) -> httpcore.AsyncNetworkStream:
            nonlocal permitted, stream
            connected.append(host)
            stream = Stream([])
            if mode == "revoked_connect":
                permitted = False
            return stream

    backend = PublicNetworkBackend(guard, resolver=resolver, delegate=Backend())
    with pytest.raises(ConnectorFailure):
        await backend.connect_tcp(HOST, 443)
    if mode == "revoked_dns":
        assert not connected
    else:
        assert connected == [PUBLIC_IP] and stream is not None and stream._closed


@pytest.mark.parametrize("setting", ["max_wire_bytes", "max_total_bytes"])
async def test_download_and_execution_byte_budgets_are_enforced(setting: str) -> None:
    http = client(lambda request: reply(b"12345"), **{setting: 4})
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "SIZE_LIMIT"
    await http.aclose()


async def test_page_budget_redirect_budget_and_identity_scope() -> None:
    http = client(lambda request: reply(), max_pages=1)
    await http.get(URL)
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "PAGE_LIMIT" and http.budget.requests == 1
    await http.aclose()
    http = client(lambda request: reply(status=302, headers={"location": "/jobs"}), max_redirects=1)
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "REDIRECT_LIMIT" and http.budget.requests == 2
    await http.aclose()
    auth = access()

    async def provider() -> CollectionAuthorization:
        return auth

    http = CollectionHttpClient(
        provider,
        CollectionLimits(),
        CollectionCoordinator(),
        transport=httpx.MockTransport(lambda request: reply()),
    )
    await http.get(URL)
    auth = replace(auth, owner_id=uuid4())
    with pytest.raises(ConnectorFailure) as error:
        await http.get(URL)
    assert error.value.code == "NOT_PERMITTED" and http.budget.requests == 1
    await http.aclose()


async def test_manual_paginated_contract_still_cannot_collect() -> None:
    with pytest.raises(ConnectorFailure) as error:
        await ManualConnector().fetch_page(ConnectorQuery())
    assert error.value.code == "MANUAL_ONLY"
