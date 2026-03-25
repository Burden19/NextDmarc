from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.rbac import Role, parse_role
from app.db.session import get_db_session


@dataclass(slots=True)
class TenantContext:
    tenant_id: UUID


async def get_settings_dependency() -> Settings:
    return get_settings()


async def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str):
        return request_id
    raise AppError(message="Request ID is not available in context", status_code=500)


async def get_tenant_context(x_tenant_id: str = Header(alias="X-Tenant-ID")) -> TenantContext:
    try:
        return TenantContext(tenant_id=UUID(x_tenant_id))
    except ValueError as exc:
        raise AppError(
            message="Invalid X-Tenant-ID header",
            status_code=400,
            code="invalid_tenant",
        ) from exc


async def get_current_role(x_role: str = Header(alias="X-Role")) -> Role:
    return parse_role(x_role)


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session
