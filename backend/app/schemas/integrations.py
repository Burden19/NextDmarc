from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

IntegrationKind = Literal["email", "slack", "siem"]


class IntegrationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: IntegrationKind
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class IntegrationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    config: dict[str, Any] | None = None
    enabled: bool | None = None


class IntegrationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    kind: IntegrationKind
    config: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class IntegrationTestResponse(BaseModel):
    integration_id: UUID
    status: str
    detail: str
