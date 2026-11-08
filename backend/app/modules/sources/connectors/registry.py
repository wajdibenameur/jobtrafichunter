from collections.abc import Callable

from app.modules.sources.connectors.access import CollectionAuthorization
from app.modules.sources.connectors.contracts import ConnectorFailure, JobSourceConnector
from app.modules.sources.connectors.manual_import import ManualConnector


def connector_for(integration_type: str) -> JobSourceConnector:
    """Only implemented, deliberately manual workflows can be resolved."""
    if integration_type in {"LINK_ONLY", "MANUAL_IMPORT"}:
        return ManualConnector()
    raise ConnectorFailure("UNAVAILABLE", "No connector is registered for this integration")


class ConnectorRegistry:
    """Internal extension point; no automatic provider is registered by default."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], JobSourceConnector]] = {}

    def register(self, kind: str, factory: Callable[[], JobSourceConnector]) -> None:
        if kind in {"LINK_ONLY", "MANUAL_IMPORT"} or kind in self._factories:
            raise ConnectorFailure("CONFIGURATION", "Connector kind is already reserved")
        self._factories[kind] = factory

    def resolve(
        self, kind: str, authorization: CollectionAuthorization | None = None
    ) -> JobSourceConnector:
        if kind in {"LINK_ONLY", "MANUAL_IMPORT"}:
            return connector_for(kind)
        if authorization is None:
            raise ConnectorFailure("NOT_PERMITTED", "Automatic connector requires authorization")
        authorization.require()
        factory = self._factories.get(kind)
        if factory is None:
            raise ConnectorFailure("UNAVAILABLE", "No connector is registered for this integration")
        return factory()
