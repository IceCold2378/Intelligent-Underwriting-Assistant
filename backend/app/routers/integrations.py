"""
Integration management API endpoints.

Provides CRUD for integration connections, health checks,
data sync triggers, and webhook management.
"""

import uuid
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.integrations.base import integration_registry
from app.integrations.webhooks import webhook_manager, WebhookEndpoint, WebhookEvent
from app.models.schemas import (
    IntegrationListResponse,
    IntegrationConnectRequest,
    IntegrationSyncRequest,
    IntegrationSyncResponse,
    WebhookCreateRequest,
    WebhookListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ── List Integrations ─────────────────────────────────────────────

@router.get("", response_model=IntegrationListResponse)
async def list_integrations(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all registered integrations with their status."""
    integrations = integration_registry.list_all()
    health = await integration_registry.health_check_all()
    return IntegrationListResponse(
        integrations=integrations,
        health=health,
    )


# ── Connect Integration ──────────────────────────────────────────

@router.post("/{name}/connect")
async def connect_integration(
    name: str,
    body: IntegrationConnectRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Connect to an external integration by name."""
    integration = integration_registry.get(name)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{name}' not found. Available: "
                   f"{[i['name'] for i in integration_registry.list_all()]}",
        )

    success = await integration_registry.connect(name, body.config)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect '{name}': {integration.last_error}",
        )

    logger.info("User %s connected integration '%s'", current_user.get("email"), name)
    return {
        "message": f"Connected to {integration.display_name}",
        "integration": integration.get_info(),
    }


# ── Disconnect Integration ────────────────────────────────────────

@router.post("/{name}/disconnect")
async def disconnect_integration(
    name: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Disconnect an integration."""
    integration = integration_registry.get(name)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{name}' not found",
        )

    await integration_registry.disconnect(name)
    logger.info("User %s disconnected integration '%s'", current_user.get("email"), name)
    return {"message": f"Disconnected from {integration.display_name}"}


# ── Sync Data ─────────────────────────────────────────────────────

@router.post("/{name}/sync", response_model=IntegrationSyncResponse)
async def sync_integration(
    name: str,
    body: IntegrationSyncRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Trigger a data sync with an integration."""
    integration = integration_registry.get(name)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{name}' not found",
        )

    if not integration.is_connected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integration '{name}' is not connected",
        )

    result = await integration.sync_data(
        direction=body.direction,
        **(body.params or {}),
    )

    return IntegrationSyncResponse(
        integration=name,
        direction=body.direction,
        result=result,
    )


# ── Health Check (single integration) ─────────────────────────────

@router.get("/{name}/health")
async def integration_health(
    name: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Check health of a specific integration."""
    integration = integration_registry.get(name)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{name}' not found",
        )

    health = await integration.health_check()
    return {
        "integration": name,
        "health": health.to_dict(),
    }


# ══════════════════════════════════════════════════════════════════
#  Webhooks
# ══════════════════════════════════════════════════════════════════

@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Register a new webhook endpoint."""
    endpoint_id = f"wh_{uuid.uuid4().hex[:12]}"
    secret = uuid.uuid4().hex

    # Parse event list
    try:
        events = [WebhookEvent(e) for e in body.events]
    except ValueError as e:
        valid_events = [ev.value for ev in WebhookEvent]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid event: {e}. Valid: {valid_events}",
        )

    endpoint = WebhookEndpoint(
        id=endpoint_id,
        url=body.url,
        events=events,
        secret=secret,
        user_id=current_user.get("id"),
        description=body.description or "",
    )
    webhook_manager.register(endpoint)

    logger.info("User %s created webhook %s → %s",
                current_user.get("email"), endpoint_id, body.url)

    return {
        "id": endpoint_id,
        "secret": secret,  # Return once; client must store it
        "message": "Webhook registered. Store the secret — it won't be shown again.",
    }


@router.get("/webhooks", response_model=WebhookListResponse)
async def list_webhooks(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all webhooks for the current user."""
    user_id = current_user.get("id")
    endpoints = webhook_manager.list_all(user_id=user_id)
    return WebhookListResponse(webhooks=endpoints)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a webhook endpoint."""
    endpoint = webhook_manager.get(webhook_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found",
        )

    # Verify ownership
    if endpoint.user_id != current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own webhooks",
        )

    webhook_manager.unregister(webhook_id)
    return {"message": f"Webhook {webhook_id} deleted"}
