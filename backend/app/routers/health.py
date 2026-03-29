"""
Health check router.
"""

import time
import logging

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse, ServiceStatus

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    System health check — reports status of all dependent services.
    """
    services = []

    # Check Vector DB / Retriever
    try:
        from app.services.vector_service import get_retriever
        start = time.time()
        retriever = get_retriever()
        latency = round((time.time() - start) * 1000, 1)
        services.append(ServiceStatus(
            name="vector_db",
            status="healthy" if retriever else "unhealthy",
            latency_ms=latency,
        ))
    except Exception as e:
        logger.warning("Vector DB health check failed: %s", e)
        services.append(ServiceStatus(name="vector_db", status="unhealthy"))

    # Check RAG Chain
    try:
        from app.services.ai_service import get_rag_chain
        chain = get_rag_chain()
        services.append(ServiceStatus(
            name="rag_chain",
            status="healthy" if chain else "unhealthy",
        ))
    except Exception:
        services.append(ServiceStatus(name="rag_chain", status="unhealthy"))

    # Overall status
    all_healthy = all(s.status == "healthy" for s in services)
    any_healthy = any(s.status == "healthy" for s in services)

    if all_healthy:
        overall = "healthy"
    elif any_healthy:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT.value,
        services=services,
    )
