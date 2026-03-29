"""
Webhook manager for event-driven notifications.

Triggers webhooks when analysis completes, allowing external systems
to react to underwriting results. Supports HMAC signature verification,
configurable retry logic with exponential backoff, and per-user endpoints.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

import requests

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────

class WebhookEvent(str, Enum):
    ANALYSIS_COMPLETE = "analysis.complete"
    ANALYSIS_FAILED = "analysis.failed"
    HIGH_RISK_DETECTED = "analysis.high_risk"
    USER_REGISTERED = "user.registered"
    INTEGRATION_STATUS = "integration.status_change"


@dataclass
class WebhookEndpoint:
    """A registered webhook endpoint."""
    id: str
    url: str
    events: list[WebhookEvent]
    secret: str  # HMAC signing key
    active: bool = True
    user_id: int | None = None
    description: str = ""
    created_at: float = field(default_factory=time.time)
    last_triggered: float | None = None
    failure_count: int = 0
    max_retries: int = 3


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""
    endpoint_id: str
    event: str
    status_code: int | None = None
    success: bool = False
    duration_ms: float = 0.0
    error: str | None = None
    attempt: int = 1
    timestamp: float = field(default_factory=time.time)


# ── Webhook Manager ───────────────────────────────────────────────

class WebhookManager:
    """
    Manages webhook endpoints and event delivery.

    Usage:
        manager = WebhookManager()
        manager.register(endpoint)
        await manager.trigger("analysis.complete", payload)
    """

    def __init__(self):
        self._endpoints: dict[str, WebhookEndpoint] = {}

    def register(self, endpoint: WebhookEndpoint) -> None:
        """Register a new webhook endpoint."""
        self._endpoints[endpoint.id] = endpoint
        logger.info(
            "Webhook registered: id=%s, url=%s, events=%s",
            endpoint.id, endpoint.url, [e.value for e in endpoint.events],
        )

    def unregister(self, endpoint_id: str) -> bool:
        """Remove a webhook endpoint."""
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            logger.info("Webhook unregistered: id=%s", endpoint_id)
            return True
        return False

    def get(self, endpoint_id: str) -> WebhookEndpoint | None:
        """Get a webhook by ID."""
        return self._endpoints.get(endpoint_id)

    def list_all(self, user_id: int | None = None) -> list[dict]:
        """List all registered webhooks, optionally filtered by user."""
        endpoints = self._endpoints.values()
        if user_id is not None:
            endpoints = [e for e in endpoints if e.user_id == user_id]
        return [
            {
                "id": e.id,
                "url": e.url,
                "events": [ev.value for ev in e.events],
                "active": e.active,
                "description": e.description,
                "failure_count": e.failure_count,
                "last_triggered": e.last_triggered,
            }
            for e in endpoints
        ]

    def update(self, endpoint_id: str, **kwargs) -> bool:
        """Update a webhook endpoint's properties."""
        endpoint = self._endpoints.get(endpoint_id)
        if not endpoint:
            return False
        for key, value in kwargs.items():
            if hasattr(endpoint, key):
                setattr(endpoint, key, value)
        return True

    async def trigger(
        self,
        event: str | WebhookEvent,
        payload: dict,
    ) -> list[WebhookDelivery]:
        """
        Trigger all webhooks registered for the given event.

        Args:
            event: Event name or WebhookEvent enum
            payload: JSON-serializable payload to deliver

        Returns:
            List of delivery results
        """
        event_str = event.value if isinstance(event, WebhookEvent) else event
        deliveries: list[WebhookDelivery] = []

        # Find matching endpoints
        matching = [
            ep for ep in self._endpoints.values()
            if ep.active and any(e.value == event_str for e in ep.events)
        ]

        if not matching:
            logger.debug("No webhooks registered for event: %s", event_str)
            return deliveries

        logger.info("Triggering %d webhooks for event: %s", len(matching), event_str)

        for endpoint in matching:
            delivery = await self._deliver(endpoint, event_str, payload)
            deliveries.append(delivery)

        return deliveries

    async def _deliver(
        self,
        endpoint: WebhookEndpoint,
        event: str,
        payload: dict,
    ) -> WebhookDelivery:
        """Deliver a webhook with retry logic and HMAC signing."""
        body = json.dumps({
            "event": event,
            "payload": payload,
            "timestamp": time.time(),
        }, default=str)

        # HMAC signature
        signature = hmac.new(
            endpoint.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event,
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Id": endpoint.id,
            "User-Agent": "UnderwritingAgent/3.0",
        }

        for attempt in range(1, endpoint.max_retries + 1):
            start = time.time()
            try:
                response = requests.post(
                    endpoint.url,
                    data=body,
                    headers=headers,
                    timeout=10,
                )
                duration = (time.time() - start) * 1000
                success = 200 <= response.status_code < 300

                delivery = WebhookDelivery(
                    endpoint_id=endpoint.id,
                    event=event,
                    status_code=response.status_code,
                    success=success,
                    duration_ms=duration,
                    attempt=attempt,
                )

                if success:
                    endpoint.last_triggered = time.time()
                    endpoint.failure_count = 0
                    logger.info(
                        "Webhook delivered: id=%s, status=%d, time=%.1fms",
                        endpoint.id, response.status_code, duration,
                    )
                    return delivery

                logger.warning(
                    "Webhook failed: id=%s, status=%d, attempt=%d/%d",
                    endpoint.id, response.status_code, attempt, endpoint.max_retries,
                )

            except requests.RequestException as e:
                duration = (time.time() - start) * 1000
                delivery = WebhookDelivery(
                    endpoint_id=endpoint.id,
                    event=event,
                    success=False,
                    duration_ms=duration,
                    error=str(e),
                    attempt=attempt,
                )
                logger.warning(
                    "Webhook error: id=%s, error=%s, attempt=%d/%d",
                    endpoint.id, e, attempt, endpoint.max_retries,
                )

            # Exponential backoff between retries
            if attempt < endpoint.max_retries:
                delay = (2 ** (attempt - 1)) * 0.5  # 0.5s, 1s, 2s
                import asyncio
                await asyncio.sleep(delay)

        # All retries exhausted
        endpoint.failure_count += 1
        if endpoint.failure_count >= 5:
            endpoint.active = False
            logger.warning(
                "Webhook auto-disabled after %d failures: id=%s",
                endpoint.failure_count, endpoint.id,
            )

        return delivery  # noqa: F821 — last delivery from the loop


# Global singleton
webhook_manager = WebhookManager()
