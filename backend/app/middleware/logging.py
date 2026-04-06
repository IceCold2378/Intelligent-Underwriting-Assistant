"""
Request/response logging middleware.
"""

import time
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing, status code, and a correlation ID."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        # Attach request ID for downstream use
        request.state.request_id = request_id

        logger.info(
            "[%s] >> %s %s",
            request_id, request.method, request.url.path,
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.time() - start) * 1000, 1)
            logger.exception("[%s] ERROR %s %s -- unhandled error after %dms",
                             request_id, request.method, request.url.path, elapsed_ms)
            raise

        elapsed_ms = round((time.time() - start) * 1000, 1)
        logger.info(
            "[%s] << %s %s -- %d (%dms)",
            request_id, request.method, request.url.path,
            response.status_code, elapsed_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
