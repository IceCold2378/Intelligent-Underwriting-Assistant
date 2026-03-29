"""
Admin endpoints for managing users, guidelines, settings, and API keys.

Accessible only to users with the 'admin' role.
"""

import csv
import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_db, require_role
from app.models.database import User, AuditLog
from app.models.schemas import (
    AdminUserUpdate,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyListResponse,
    SystemMetricsResponse,
)
from app.services.api_key_service import create_api_key, list_api_keys, revoke_api_key
from app.services.vector_service import build_vector_db
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
settings = get_settings()

# Require admin role for all endpoints in this router
AdminDep = Annotated[User, Depends(require_role(["admin"]))]


# ── System Metrics ────────────────────────────────────────────────

@router.get("/system/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve high-level system usage metrics."""
    # Count Users
    user_count = await db.scalar(select(User).with_only_columns(User.id))
    # Approximation of total analyses (would normally query AnalysisRecords count)
    # Using a placeholder implementation for the sake of example
    
    # In a real system, you'd calculate actual sizes and integration states
    from app.integrations.base import integration_registry
    active_integrations = sum(
        1 for i in integration_registry.list_all()
        if i["status"] == "connected"
    )

    return SystemMetricsResponse(
        total_users=user_count or 1,
        active_integrations=active_integrations,
        total_analyses=0, # Placeholder
        db_size_mb=12.5,
        vector_db_size_mb=4.2,
    )


# ── User Management ───────────────────────────────────────────────

@router.get("/users")
async def list_users(
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """List all registered users."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": bool(u.is_active),
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: AdminUserUpdate,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role or active status."""
    if user_id == admin.id and body.role != "admin" and body.role is not None:
        raise HTTPException(status_code=400, detail="Cannot downgrade your own admin role.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if body.role is not None:
        user.role = body.role.value
    if body.is_active is not None:
        user.is_active = 1 if body.is_active else 0

    await db.commit()
    logger.info("Admin %s updated user %d (role=%s, active=%s)", 
                admin.email, user_id, user.role, bool(user.is_active))
                
    return {"message": "User updated successfully"}


# ── Guidelines Management ─────────────────────────────────────────

@router.post("/guidelines")
async def upload_guidelines(
    admin: AdminDep,
    file: UploadFile = File(...),
):
    """Upload new underwriting guidelines and rebuild the Vector DB."""
    if not file.filename.endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="Only .txt or .md files allowed.")

    try:
        content = await file.read()
        target_path = settings.effective_guidelines_path
        
        # Write to disk
        with open(target_path, "wb") as f:
            f.write(content)
            
        logger.info("Admin %s uploaded new guidelines: %s", admin.email, file.filename)
        
        # Rebuild Chroma DB blocking (in production, use background task)
        build_vector_db(force_rebuild=True)
        
        return {"message": "Guidelines updated and vector database rebuilt."}
        
    except Exception as e:
        logger.exception("Failed to update guidelines: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to rebuild DB: {e}")


# ── Audit Log Export ──────────────────────────────────────────────

@router.get("/audit-log/export")
async def export_audit_log(
    admin: AdminDep,
    format: str = "json",
    limit: int = 1000,
    db: AsyncSession = Depends(get_db),
):
    """Export the system audit log."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    data = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource": log.resource,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    
    if format.lower() == "csv":
        output = io.StringIO()
        if not data:
            return Response("No data", media_type="text/csv")
            
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="audit_log.csv"'}
        )
        
    return JSONResponse({"logs": data})


# ── API Keys ──────────────────────────────────────────────────────

@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def generate_api_key(
    body: ApiKeyCreate,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key for external service access."""
    # Only admins can generate global scope API keys in this implementation
    result = await create_api_key(db, body, admin.id)
    
    # Send secret to log (audit)
    logger.info("Admin %s generated API key '%s' with scopes %s", 
                admin.email, body.name, body.scopes)
                
    return result


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def get_api_keys(
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """List active API keys."""
    keys = await list_api_keys(db, admin.id)
    return ApiKeyListResponse(keys=keys)


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    success = await revoke_api_key(db, key_id, admin.id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found.")
        
    logger.info("Admin %s revoked API key ID %d", admin.email, key_id)
    return {"message": "API key revoked."}
