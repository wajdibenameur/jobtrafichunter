"""Server-owned collection authorization, separate from a user's manual-source toggle."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from urllib.parse import unquote
from uuid import UUID

import httpx

from app.modules.sources.connectors.contracts import ConnectorFailure
from app.modules.sources.policy import verified_automation
from app.shared.urls import public_https_url


@dataclass(frozen=True)
class AllowedRoute:
    host: str
    path_prefix: str

    def __post_init__(self) -> None:
        try:
            url = httpx.URL(public_https_url(f"https://{self.host}{self.path_prefix}"))
            if (
                url.host != self.host
                or url.path != self.path_prefix
                or url.query
                or url.fragment
                or not self.path_prefix.startswith("/")
                or any(c in self.path_prefix for c in ("%", "\\", "?", "#"))
                or any(part in {".", ".."} for part in self.path_prefix.split("/"))
            ):
                raise ValueError
        except (ValueError, httpx.InvalidURL):
            raise ConnectorFailure("CONFIGURATION", "Invalid approved route") from None


@dataclass(frozen=True)
class CollectionAuthorization:
    owner_id: UUID
    source_id: UUID
    enabled: bool
    legal_status: str
    verification: Mapping[str, object] = field(repr=False)
    routes: tuple[AllowedRoute, ...]

    def require(self) -> None:
        if (
            not self.enabled
            or not self.routes
            or not verified_automation(self.legal_status, dict(self.verification))
        ):
            raise ConnectorFailure(
                "NOT_PERMITTED", "Collection authorization is missing or expired"
            )
        # Bind the reviewed endpoint to the configured domains and paths as well.
        self.check_url(str(self.verification["api_url"]))

    def check_url(self, value: str) -> httpx.URL:
        try:
            url = httpx.URL(public_https_url(value))
            # Reject encoded/ambiguous path traversal before a server can decode it
            # differently. Queries are data, and never become a destination URL here.
            raw_path = url.raw_path.split(b"?", 1)[0].decode("ascii")
            path = unquote(raw_path)
            if (
                "%" in raw_path
                or "\\" in path
                or any(part in {".", ".."} for part in path.split("/"))
            ):
                raise ValueError
            if url.fragment or not any(
                url.host == route.host
                and (
                    path == route.path_prefix.rstrip("/")
                    or path.startswith(route.path_prefix.rstrip("/") + "/")
                )
                for route in self.routes
            ):
                raise ValueError
            return url
        except (ValueError, httpx.InvalidURL, UnicodeError):
            raise ConnectorFailure(
                "UNSAFE_URL", "URL is outside approved collection routes"
            ) from None


AuthorizationProvider = Callable[[], Awaitable[CollectionAuthorization]]
