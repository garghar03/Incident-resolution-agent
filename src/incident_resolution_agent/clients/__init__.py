"""External log source clients."""

from incident_resolution_agent.analyzers.clients.loki_client import LokiClient
from incident_resolution_agent.analyzers.clients.splunk_client import SplunkClient

__all__ = ["LokiClient", "SplunkClient"]
