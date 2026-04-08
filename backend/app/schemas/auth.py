from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)
    tenant_id: UUID


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=1)


class RegisterTenantRequest(BaseModel):
    tenant_name: str = Field(min_length=1, max_length=200)
    admin_email: str = Field(min_length=3, max_length=320)
    admin_password: str = Field(min_length=8, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    csrf_token: str | None = None
    token_type: str = "bearer"


class RegisterTenantResponse(BaseModel):
    tenant_id: UUID
    user_id: UUID
    role: str
    message: str
