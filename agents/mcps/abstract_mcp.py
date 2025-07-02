from abc import ABC, abstractmethod
from typing import Any, Dict


class AbstractMCPClient(ABC):
    """
    Abstract base class for Model Context Protocol (MCP) integration.
    Implementations should provide methods to query context and fetch evidence from MCP servers (e.g., K8s-MCP-Server, Prometheus-MCP-Server).
    """

    @abstractmethod
    def query_context(self, query: str, params: Dict[str, Any] = None) -> Any:
        """
        Query the MCP server for context information.
        Args:
            query: The query string or identifier.
            params: Optional parameters for the query.
        Returns:
            The context information returned by the MCP server.
        """
        pass

    @abstractmethod
    def fetch_evidence(self, incident_id: str, context_type: str = None) -> Any:
        """
        Fetch evidence or data related to a specific incident from the MCP server.
        Args:
            incident_id: The unique identifier for the incident.
            context_type: Optional type of context/evidence to fetch (e.g., logs, metrics).
        Returns:
            The evidence or data fetched from the MCP server.
        """
        pass

    @abstractmethod
    def close(self):
        """
        Clean up any resources or connections held by the MCP client.
        """
        pass
