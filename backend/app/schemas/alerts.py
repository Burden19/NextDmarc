from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AlertSeverityValue = Literal["low", "medium", "high", "critical"]


class AlertResponse(BaseModel):
    id: str
    tenant_id: str
    domain_id: str | None
    severity: str
    status: str
    message: str
    assignee: str | None
    escalation_level: int
    created_at: datetime
    updated_at: datetime


class AlertAuditResponse(BaseModel):
    id: str
    tenant_id: str
    alert_id: str
    action: str
    actor: str | None
    comment: str | None
    details: dict[str, Any]
    created_at: datetime


class AlertTriageResponse(BaseModel):
    alert: AlertResponse
    audit: AlertAuditResponse


class PaginatedAlertsResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_previous: bool


class AlertStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=2, max_length=32)
    actor: str | None = Field(default=None, max_length=320)
    comment: str | None = Field(default=None, max_length=4000)


class AlertAssignRequest(BaseModel):
    assignee: str = Field(min_length=1, max_length=320)
    actor: str | None = Field(default=None, max_length=320)
    comment: str | None = Field(default=None, max_length=4000)


class AlertCommentRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=4000)
    actor: str | None = Field(default=None, max_length=320)


class AlertEscalateRequest(BaseModel):
    actor: str | None = Field(default=None, max_length=320)
    comment: str | None = Field(default=None, max_length=4000)
    target_severity: AlertSeverityValue | None = None
