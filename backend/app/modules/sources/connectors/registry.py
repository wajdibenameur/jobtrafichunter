from app.modules.sources.connectors.contracts import ConnectorFailure, JobSourceConnector
from app.modules.sources.connectors.manual_import import ManualConnector


def connector_for(integration_type: str) -> JobSourceConnector:
    """Only implemented, deliberately manual workflows can be resolved."""
    if integration_type in {"LINK_ONLY", "MANUAL_IMPORT"}:
        return ManualConnector()
    raise ConnectorFailure("UNAVAILABLE", "No connector is registered for this integration")
