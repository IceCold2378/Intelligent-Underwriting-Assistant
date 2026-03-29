"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


# ── Enums ──────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class UserRole(str, Enum):
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    COMPLIANCE_OFFICER = "compliance_officer"
    ADMIN = "admin"


# ── Auth Schemas ───────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=100)
    organization: str | None = Field(None, max_length=200)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseModel):
    id: int
    email: str
    full_name: str
    organization: str | None
    role: UserRole
    created_at: datetime
    analysis_count: int = 0

    model_config = {"from_attributes": True}


# ── Analysis Schemas ───────────────────────────────────────────────

class RiskFlag(BaseModel):
    """A single risk identified in the application."""
    category: str = Field(..., description="Risk category (e.g., 'Credit Score', 'DTI Ratio')")
    description: str = Field(..., description="Description of the risk")
    severity: RiskLevel = Field(..., description="Risk severity level")
    guideline_reference: str = Field(..., description="Which guideline was violated")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")


class AnalysisResult(BaseModel):
    """Structured analysis output from the AI pipeline."""
    summary: str = Field(..., description="Brief summary of the loan application")
    overall_risk_score: int = Field(..., ge=0, le=100, description="Overall risk score 0-100")
    overall_risk_level: RiskLevel
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    recommendation: str = Field(..., description="Approve / Deny / Manual Review")
    detailed_analysis: str = Field(..., description="Full analysis text")
    guidelines_checked: int = Field(0, description="Number of guidelines checked")
    processing_time_seconds: float = 0.0


class AnalysisResponse(BaseModel):
    """API response wrapping the analysis result."""
    id: int | None = None
    filename: str
    analysis: AnalysisResult
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AnalysisHistoryItem(BaseModel):
    """Compact item for the analysis history list."""
    id: int
    filename: str
    overall_risk_score: int
    overall_risk_level: RiskLevel
    recommendation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisHistoryResponse(BaseModel):
    """Paginated analysis history."""
    items: list[AnalysisHistoryItem]
    total: int
    page: int
    page_size: int


# ── Health Schemas ─────────────────────────────────────────────────

class ServiceStatus(BaseModel):
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: list[ServiceStatus] = []


# ── Dashboard / Metrics ───────────────────────────────────────────

class DashboardMetrics(BaseModel):
    total_analyses: int = 0
    analyses_today: int = 0
    avg_risk_score: float = 0.0
    risk_distribution: dict[str, int] = Field(
        default_factory=lambda: {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    )
    recent_analyses: list[AnalysisHistoryItem] = []


# ── Integration Schemas ───────────────────────────────────────────

class IntegrationListResponse(BaseModel):
    """Response from GET /integrations."""
    integrations: list[dict] = []
    health: dict[str, dict] = {}


class IntegrationConnectRequest(BaseModel):
    """Request body for connecting an integration."""
    config: dict = Field(default_factory=dict, description="Integration-specific config")


class IntegrationSyncRequest(BaseModel):
    """Request body for triggering a data sync."""
    direction: str = Field("push", description="'push' or 'pull'")
    params: dict | None = Field(None, description="Sync-specific parameters")


class IntegrationSyncResponse(BaseModel):
    """Response from a data sync operation."""
    integration: str
    direction: str
    result: dict


# ── Webhook Schemas ───────────────────────────────────────────────

class WebhookCreateRequest(BaseModel):
    """Request body for creating a webhook."""
    url: str = Field(..., description="HTTPS endpoint to deliver events to")
    events: list[str] = Field(
        ...,
        description="Events to subscribe to (e.g., 'analysis.complete')",
    )
    description: str | None = None


class WebhookListResponse(BaseModel):
    """Response from GET /webhooks."""
    webhooks: list[dict] = []


# ── Admin Schemas ─────────────────────────────────────────────────

class AdminUserUpdate(BaseModel):
    """Request to update a user's role/active status."""
    role: UserRole | None = None
    is_active: bool | None = None


class AuditLogExport(BaseModel):
    """Schema for exporting audit logs."""
    format: str = Field("json", description="json or csv")
    start_date: datetime | None = None
    end_date: datetime | None = None


class SystemMetricsResponse(BaseModel):
    """Response for system metrics."""
    total_users: int
    active_integrations: int
    total_analyses: int
    db_size_mb: float | None = None
    vector_db_size_mb: float | None = None


# ── API Key Schemas ───────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    """Request to create a new API key."""
    name: str = Field(..., max_length=100)
    scopes: list[str] = Field(default=["read", "write"])
    expires_in_days: int | None = Field(None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    """Response when an API key is created (includes the raw key)."""
    id: int
    name: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime
    # The actual plain-text key - only returned ONCE upon creation
    api_key: str | None = None


class ApiKeyListResponse(BaseModel):
    """Response when listing API keys (does not include the raw key)."""
    keys: list[ApiKeyResponse]


# ── Task & Streaming Schemas ──────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class TaskResponse(BaseModel):
    """Response representing a background task."""
    task_id: str
    task_type: str
    status: TaskStatus
    progress: float
    created_at: datetime
    updated_at: datetime


class StreamEvent(BaseModel):
    """A Server-Sent Event payload."""
    event: str  # Type of event (e.g., "agent_step", "complete")
    data: dict  # The payload data

