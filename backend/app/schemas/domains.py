from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DomainCreateRequest(BaseModel):
    fqdn: str = Field(min_length=1, max_length=255)
    dmarc_policy: str = Field(default="none", min_length=1, max_length=64)


class DomainUpdateRequest(BaseModel):
    fqdn: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    dmarc_policy: str | None = Field(default=None, min_length=1, max_length=64)


class DomainResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    fqdn: str
    status: str
    dmarc_policy: str
    created_at: datetime
    updated_at: datetime


class DomainPolicyResponse(BaseModel):
    domain_id: UUID
    fqdn: str
    dmarc_policy: str
