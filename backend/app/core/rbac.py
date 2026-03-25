from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Final

from fastapi import Header

from app.core.exceptions import AppError


class Role(StrEnum):
    NEXTSTEP_ADMIN = "nextstep_admin"
    CLIENT_ADMIN = "client_admin"
    ANALYST_SOC = "analyst_soc"
    CLIENT_USER = "client_user"


class Permission(StrEnum):
    OVERVIEW_READ = "overview:read"
    DASHBOARD_READ = "dashboard:read"
    DOMAINS_READ = "domains:read"
    DOMAINS_WRITE = "domains:write"
    REPORTS_READ = "reports:read"
    ALERTS_READ = "alerts:read"
    ALERTS_TRIAGE = "alerts:triage"
    SCORING_READ = "scoring:read"
    RECOMMENDATIONS_READ = "recommendations:read"
    RECOMMENDATIONS_RESOLVE = "recommendations:resolve"
    INTEGRATIONS_READ = "integrations:read"
    INTEGRATIONS_WRITE = "integrations:write"
    GOVERNANCE_READ = "governance:read"
    GOVERNANCE_WRITE = "governance:write"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"


# Backward-compatibility with plan/docs naming.
ROLE_ALIASES: Final[dict[str, Role]] = {
    "soc_analyst": Role.ANALYST_SOC,
}


RBAC_MATRIX: Final[dict[Role, frozenset[Permission]]] = {
    Role.NEXTSTEP_ADMIN: frozenset(Permission),
    Role.CLIENT_ADMIN: frozenset(Permission),
    Role.ANALYST_SOC: frozenset(
        {
            Permission.OVERVIEW_READ,
            Permission.DASHBOARD_READ,
            Permission.REPORTS_READ,
            Permission.ALERTS_READ,
            Permission.ALERTS_TRIAGE,
            Permission.SCORING_READ,
            Permission.RECOMMENDATIONS_READ,
        }
    ),
    Role.CLIENT_USER: frozenset(
        {
            Permission.OVERVIEW_READ,
            Permission.DASHBOARD_READ,
            Permission.REPORTS_READ,
            Permission.RECOMMENDATIONS_READ,
        }
    ),
}


def parse_role(raw_role: str) -> Role:
    normalized = raw_role.strip().lower()

    if normalized in ROLE_ALIASES:
        return ROLE_ALIASES[normalized]

    try:
        return Role(normalized)
    except ValueError as exc:
        raise AppError(
            message=f"Unknown role: {raw_role}",
            status_code=400,
            code="invalid_role",
        ) from exc


def permissions_for_role(role: Role | str) -> frozenset[Permission]:
    parsed_role = parse_role(role) if isinstance(role, str) else role
    return RBAC_MATRIX.get(parsed_role, frozenset())


def is_allowed(*, role: Role | str, permission: Permission) -> bool:
    return permission in permissions_for_role(role)


def enforce_permission(*, role: Role | str, permission: Permission) -> None:
    if is_allowed(role=role, permission=permission):
        return

    parsed_role = parse_role(role) if isinstance(role, str) else role
    raise AppError(
        message="Permission denied",
        status_code=403,
        code="forbidden",
        details={"role": parsed_role.value, "permission": permission.value},
    )


def permission_dependency(permission: Permission) -> Callable[..., Awaitable[None]]:
    async def dependency(x_role: str = Header(alias="X-Role")) -> None:
        enforce_permission(role=x_role, permission=permission)

    return dependency
