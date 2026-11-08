"""IP-pinned HTTPCore backend; Host, certificate verification and SNI stay intact."""

import asyncio
import ipaddress
import socket
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable, Iterable

import httpcore
import httpx

from app.modules.sources.connectors.contracts import ConnectorFailure

Resolver = Callable[[str], Awaitable[list[str]]]
HostGuard = Callable[[str], Awaitable[None]]


async def resolve_public(host: str) -> list[str]:
    records = await asyncio.get_running_loop().getaddrinfo(
        host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
    )
    return list(dict.fromkeys(str(record[4][0]) for record in records))


def checked_ip(value: str) -> str:
    try:
        ip = ipaddress.ip_address(value)
        if (
            not ip.is_global
            or ip.is_multicast
            or ip.is_reserved
            or "%" in value
            or (
                isinstance(ip, ipaddress.IPv6Address)
                and (ip.ipv4_mapped or ip.sixtofour or ip.teredo)
            )
        ):
            raise ValueError
        return str(ip)
    except ValueError:
        raise ConnectorFailure(
            "UNSAFE_ADDRESS", "Destination is not a public unicast address"
        ) from None


class PublicNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(
        self,
        guard: HostGuard,
        *,
        resolver: Resolver = resolve_public,
        delegate: httpcore.AsyncNetworkBackend | None = None,
    ) -> None:
        self.guard, self.resolver = guard, resolver
        self.delegate = delegate or httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,  # noqa: ASYNC109 - HTTPCore public override signature
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        if port != 443 or local_address is not None:
            raise ConnectorFailure("UNSAFE_ADDRESS", "Only public HTTPS connections are supported")
        async with asyncio.timeout(timeout):
            await self.guard(host)
            addresses = await self.resolver(host)
            if not addresses or len(addresses) > 32:
                raise ConnectorFailure("DNS_ERROR", "Destination resolution failed")
            # Reject the entire mixed public/private answer, not only its first address.
            pinned = [checked_ip(value) for value in addresses]
            await self.guard(host)  # Authorization may change while DNS is pending.
            stream = await self.delegate.connect_tcp(
                pinned[0], port, timeout=timeout, socket_options=socket_options
            )
            peer = stream.get_extra_info("server_addr")
            try:
                if not isinstance(peer, tuple) or checked_ip(str(peer[0])) != pinned[0]:
                    raise ConnectorFailure(
                        "UNSAFE_ADDRESS", "Connection peer does not match approved IP"
                    )
                await self.guard(host)
            except BaseException:
                await stream.aclose()
                raise
            return stream


class _ResponseStream(httpx.AsyncByteStream):
    def __init__(self, response: httpcore.Response) -> None:
        self.response = response

    async def __aiter__(self) -> AsyncIterator[bytes]:
        assert isinstance(self.response.stream, AsyncIterable)
        async for chunk in self.response.stream:
            yield chunk

    async def aclose(self) -> None:
        await self.response.aclose()


class PinnedTransport(httpx.AsyncBaseTransport):
    def __init__(self, backend: PublicNetworkBackend) -> None:
        self.pool = httpcore.AsyncConnectionPool(
            network_backend=backend,
            max_connections=4,
            max_keepalive_connections=0,
            retries=0,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self.pool.handle_async_request(
            httpcore.Request(
                method=request.method,
                url=httpcore.URL(
                    scheme=request.url.raw_scheme,
                    host=request.url.raw_host,
                    port=request.url.port,
                    target=request.url.raw_path,
                ),
                headers=request.headers.raw,
                content=b"",
                extensions=request.extensions,
            )
        )
        return httpx.Response(
            response.status,
            headers=response.headers,
            stream=_ResponseStream(response),
            request=request,
        )

    async def aclose(self) -> None:
        await self.pool.aclose()
