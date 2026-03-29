"""
Custom exception classes and global exception handlers.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


# ── Custom Exceptions ──────────────────────────────────────────────

class AppException(Exception):
    """Base exception for the application."""
    def __init__(self, message: str, status_code: int = 500, detail: str | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


class DocumentParsingError(AppException):
    """Raised when a document cannot be parsed."""
    def __init__(self, message: str = "Failed to parse the uploaded document."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class UnsupportedFileTypeError(AppException):
    """Raised when an unsupported file type is uploaded."""
    def __init__(self, filename: str):
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "unknown"
        super().__init__(
            message=f"Unsupported file type: .{ext}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class FileTooLargeError(AppException):
    """Raised when uploaded file exceeds size limit."""
    def __init__(self, max_mb: int):
        super().__init__(
            message=f"File exceeds maximum size of {max_mb} MB.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class AIServiceError(AppException):
    """Raised when the AI/LLM service fails."""
    def __init__(self, message: str = "AI analysis service encountered an error."):
        super().__init__(message=message, status_code=status.HTTP_502_BAD_GATEWAY)


class VectorDBError(AppException):
    """Raised when the vector database is unavailable."""
    def __init__(self, message: str = "Vector database is unavailable."):
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class AuthenticationError(AppException):
    """Raised on authentication failure."""
    def __init__(self, message: str = "Invalid credentials."):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppException):
    """Raised when user lacks required permissions."""
    def __init__(self, message: str = "Insufficient permissions."):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            message=f"{resource} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


# ── Global Exception Handlers ─────────────────────────────────────

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all custom application exceptions."""
    logger.warning(
        "AppException: %s | Path: %s | Status: %d",
        exc.message, request.url.path, exc.status_code
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leak stack traces."""
    logger.exception("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "An unexpected internal error occurred.",
            "detail": str(exc) if __debug__ else None,
        },
    )
