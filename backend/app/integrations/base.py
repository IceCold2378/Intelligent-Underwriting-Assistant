"""
Integration base classes and registry.

All enterprise connectors inherit from IntegrationBase, which defines
the contract for connect/disconnect/health/sync operations.

IntegrationRegistry discovers and manages all registered integrations,
providing a single entry point for the API layer.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Connection Status ─────────────────────────────────────────────

class IntegrationStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class IntegrationHealth:
    """Health check result for an integration."""
    status: IntegrationStatus
    latency_ms: float | None = None
    message: str = ""
    last_checked: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 1) if self.latency_ms else None,
            "message": self.message,
            "last_checked": self.last_checked,
        }


# ── Abstract Base ─────────────────────────────────────────────────

class IntegrationBase(ABC):
    """
    Abstract base class for all enterprise integrations.

    Subclasses must implement:
      - connect()     — establish connection to the external service
      - disconnect()  — tear down connection
      - health_check() — verify the connection is alive
      - sync_data()   — push/pull data (bidirectional sync)
    """

    # Override in subclass
    name: str = "unknown"
    display_name: str = "Unknown Integration"
    description: str = ""
    icon: str = "🔗"

    def __init__(self):
        self._status: IntegrationStatus = IntegrationStatus.DISCONNECTED
        self._config: dict[str, Any] = {}
        self._last_error: str | None = None
        self._connected_at: float | None = None

    @property
    def status(self) -> IntegrationStatus:
        return self._status

    @property
    def is_connected(self) -> bool:
        return self._status == IntegrationStatus.CONNECTED

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def configure(self, config: dict[str, Any]) -> None:
        """Set configuration for the integration."""
        self._config = config
        logger.info("%s: configured with %d settings", self.name, len(config))

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection. Returns True on success."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Tear down connection."""
        ...

    @abstractmethod
    async def health_check(self) -> IntegrationHealth:
        """Check if the connection is alive and healthy."""
        ...

    @abstractmethod
    async def sync_data(self, direction: str = "push", **kwargs) -> dict:
        """
        Sync data between this system and the integration.

        Args:
            direction: "push" (export to integration) or "pull" (import from)
            **kwargs: Integration-specific parameters

        Returns:
            Dict with sync results (records_synced, errors, etc.)
        """
        ...

    def get_info(self) -> dict:
        """Return serializable info about this integration."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "status": self._status.value,
            "last_error": self._last_error,
            "connected_at": self._connected_at,
            "configured": bool(self._config),
        }


# ── Registry ──────────────────────────────────────────────────────

class IntegrationRegistry:
    """
    Central registry for all configured integrations.
    Provides discovery, lifecycle management, and health monitoring.
    """

    def __init__(self):
        self._integrations: dict[str, IntegrationBase] = {}

    def register(self, integration: IntegrationBase) -> None:
        """Register an integration instance."""
        self._integrations[integration.name] = integration
        logger.info("Registered integration: %s (%s)",
                    integration.name, integration.display_name)

    def get(self, name: str) -> IntegrationBase | None:
        """Get an integration by name."""
        return self._integrations.get(name)

    def list_all(self) -> list[dict]:
        """List all registered integrations with their status."""
        return [i.get_info() for i in self._integrations.values()]

    async def connect(self, name: str, config: dict[str, Any] | None = None) -> bool:
        """Connect a specific integration."""
        integration = self.get(name)
        if not integration:
            logger.error("Integration not found: %s", name)
            return False

        if config:
            integration.configure(config)

        try:
            integration._status = IntegrationStatus.CONNECTING
            result = await integration.connect()
            if result:
                integration._status = IntegrationStatus.CONNECTED
                integration._connected_at = time.time()
                integration._last_error = None
                logger.info("Integration connected: %s", name)
            else:
                integration._status = IntegrationStatus.ERROR
                integration._last_error = "Connection returned False"
            return result
        except Exception as e:
            integration._status = IntegrationStatus.ERROR
            integration._last_error = str(e)
            logger.exception("Failed to connect integration %s: %s", name, e)
            return False

    async def disconnect(self, name: str) -> None:
        """Disconnect a specific integration."""
        integration = self.get(name)
        if not integration:
            return
        try:
            await integration.disconnect()
        finally:
            integration._status = IntegrationStatus.DISCONNECTED
            integration._connected_at = None
            logger.info("Integration disconnected: %s", name)

    async def health_check_all(self) -> dict[str, dict]:
        """Run health checks on all connected integrations."""
        results = {}
        for name, integration in self._integrations.items():
            if integration.is_connected:
                try:
                    health = await integration.health_check()
                    results[name] = health.to_dict()
                except Exception as e:
                    results[name] = IntegrationHealth(
                        status=IntegrationStatus.ERROR,
                        message=str(e),
                    ).to_dict()
            else:
                results[name] = IntegrationHealth(
                    status=integration.status,
                    message="Not connected",
                ).to_dict()
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all integrations (for shutdown)."""
        for name in list(self._integrations.keys()):
            await self.disconnect(name)


# Global registry singleton
integration_registry = IntegrationRegistry()
