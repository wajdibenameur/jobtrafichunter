from typing import Literal

from pydantic import ValidationError

from app.modules.sources.connectors.contracts import (
    Capabilities,
    ConnectorFailure,
    ConnectorPage,
    ConnectorQuery,
    NormalizedListing,
)


class ManualConnector:
    """No network access. User-supplied text is the only input."""

    def capabilities(self) -> Capabilities:
        return Capabilities()

    async def health_check(self) -> Literal["MANUAL_ONLY"]:
        return "MANUAL_ONLY"

    async def fetch(self, query: ConnectorQuery) -> list[NormalizedListing]:
        raise ConnectorFailure("MANUAL_ONLY", "Open the source and import the offer manually")

    async def fetch_page(self, query: ConnectorQuery) -> ConnectorPage:
        raise ConnectorFailure("MANUAL_ONLY", "Open the source and import the offer manually")

    def normalize(self, raw: dict[str, object]) -> NormalizedListing:
        try:
            return NormalizedListing.model_validate(raw)
        except ValidationError as exc:
            raise ConnectorFailure("PARSE_ERROR", "Manual offer fields are invalid") from exc
