from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MailboxCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)
    server: str = Field(min_length=1, max_length=255)
    mailbox: str = Field(default="INBOX", min_length=1, max_length=255)


class MailboxUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    username: str | None = Field(default=None, min_length=1, max_length=320)
    password: str | None = Field(default=None, min_length=1, max_length=256)
    server: str | None = Field(default=None, min_length=1, max_length=255)
    mailbox: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None


class MailboxResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    username: str
    server: str
    mailbox: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class MailboxTestResponse(BaseModel):
    mailbox_id: UUID
    status: str


class ManualTriggerResponse(BaseModel):
    mailbox_id: UUID
    status: str
