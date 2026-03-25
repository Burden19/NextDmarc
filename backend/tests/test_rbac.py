import pytest
from app.core.exceptions import AppError
from app.core.rbac import (
    Permission,
    Role,
    enforce_permission,
    is_allowed,
    parse_role,
    permissions_for_role,
)


def test_parse_role_supports_alias() -> None:
    assert parse_role("soc_analyst") == Role.ANALYST_SOC


def test_parse_role_invalid_raises() -> None:
    with pytest.raises(AppError):
        parse_role("unknown_role")


def test_client_user_has_limited_permissions() -> None:
    permissions = permissions_for_role(Role.CLIENT_USER)

    assert Permission.REPORTS_READ in permissions
    assert Permission.DOMAINS_WRITE not in permissions


def test_admin_has_all_permissions() -> None:
    assert all(
        is_allowed(role=Role.NEXTSTEP_ADMIN, permission=permission) for permission in Permission
    )


def test_enforce_permission_raises_forbidden() -> None:
    with pytest.raises(AppError) as exc_info:
        enforce_permission(role=Role.CLIENT_USER, permission=Permission.DOMAINS_WRITE)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"


def test_enforce_permission_accepts_valid_permission() -> None:
    enforce_permission(role=Role.ANALYST_SOC, permission=Permission.ALERTS_TRIAGE)
