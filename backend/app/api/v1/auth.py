from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from uuid import UUID, uuid4

from fastapi import APIRouter, status

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.rbac import Role
from app.core.security import (
    SecurityError,
    TokenPayload,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterTenantRequest,
    RegisterTenantResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@dataclass(slots=True)
class UserRecord:
    user_id: UUID
    tenant_id: UUID
    email: str
    password_hash: str
    role: Role


class InMemoryAuthStore:
    def __init__(self) -> None:
        self._users_by_scope: dict[tuple[UUID, str], UserRecord] = {}
        self._users_by_id: dict[UUID, UserRecord] = {}
        self._revoked_refresh_jti: set[str] = set()

    @staticmethod
    def _scope_key(tenant_id: UUID, email: str) -> tuple[UUID, str]:
        return (tenant_id, email.strip().lower())

    def register_tenant_admin(
        self,
        *,
        tenant_name: str,
        admin_email: str,
        admin_password: str,
    ) -> UserRecord:
        tenant_id = uuid4()
        scope_key = self._scope_key(tenant_id, admin_email)

        if scope_key in self._users_by_scope:
            raise AppError(
                message="User already exists for this tenant",
                status_code=409,
                code="user_conflict",
            )

        user = UserRecord(
            user_id=uuid4(),
            tenant_id=tenant_id,
            email=admin_email.strip().lower(),
            password_hash=hash_password(admin_password),
            role=Role.CLIENT_ADMIN,
        )
        self._users_by_scope[scope_key] = user
        self._users_by_id[user.user_id] = user
        return user

    def authenticate(self, *, tenant_id: UUID, email: str, password: str) -> UserRecord:
        scope_key = self._scope_key(tenant_id, email)
        user = self._users_by_scope.get(scope_key)

        if user is None or not verify_password(password, user.password_hash):
            raise AppError(
                message="Invalid credentials",
                status_code=401,
                code="invalid_credentials",
            )

        return user

    def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        return self._users_by_id.get(user_id)

    def revoke_refresh_jti(self, jti: str) -> None:
        self._revoked_refresh_jti.add(jti)

    def is_refresh_revoked(self, jti: str) -> bool:
        return jti in self._revoked_refresh_jti


@lru_cache(maxsize=1)
def get_auth_store() -> InMemoryAuthStore:
    return InMemoryAuthStore()


@lru_cache(maxsize=1)
def get_auth_settings() -> Settings:
    return get_settings()


def reset_auth_store_for_tests() -> None:
    get_auth_store.cache_clear()
    get_auth_settings.cache_clear()


def _ensure_jwt_keys(settings: Settings) -> None:
    if not settings.jwt_private_key or not settings.jwt_public_key:
        raise AppError(
            message="Auth is not configured: missing JWT keys",
            status_code=503,
            code="auth_unavailable",
        )


def _issue_tokens(*, settings: Settings, user: UserRecord) -> TokenResponse:
    access_token = create_token(
        subject=str(user.user_id),
        private_key=settings.jwt_private_key,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
        tenant_id=user.tenant_id,
        role=user.role.value,
        algorithm=settings.jwt_algorithm,
    )
    refresh_token = create_token(
        subject=str(user.user_id),
        private_key=settings.jwt_private_key,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
        tenant_id=user.tenant_id,
        role=user.role.value,
        algorithm=settings.jwt_algorithm,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def _decode_refresh_or_raise(*, settings: Settings, token: str) -> TokenPayload:
    try:
        return decode_token(
            token=token,
            public_key=settings.jwt_public_key,
            expected_type=TokenType.REFRESH,
            algorithms=[settings.jwt_algorithm],
        )
    except SecurityError as exc:
        raise AppError(
            message="Invalid refresh token",
            status_code=401,
            code="invalid_refresh_token",
        ) from exc


@router.post("/register-tenant", status_code=status.HTTP_201_CREATED)
async def register_tenant(payload: RegisterTenantRequest) -> RegisterTenantResponse:
    settings = get_auth_settings()
    _ensure_jwt_keys(settings)

    store = get_auth_store()
    user = store.register_tenant_admin(
        tenant_name=payload.tenant_name,
        admin_email=payload.admin_email,
        admin_password=payload.admin_password,
    )

    return RegisterTenantResponse(
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        role=user.role.value,
        message="Tenant admin account created",
    )


@router.post("/login")
async def login(payload: LoginRequest) -> TokenResponse:
    settings = get_auth_settings()
    _ensure_jwt_keys(settings)

    store = get_auth_store()
    user = store.authenticate(
        tenant_id=payload.tenant_id,
        email=payload.email,
        password=payload.password,
    )

    return _issue_tokens(settings=settings, user=user)


@router.post("/refresh")
async def refresh(payload: RefreshRequest) -> TokenResponse:
    settings = get_auth_settings()
    _ensure_jwt_keys(settings)

    store = get_auth_store()
    token_payload = _decode_refresh_or_raise(settings=settings, token=payload.refresh_token)

    if store.is_refresh_revoked(token_payload.jti):
        raise AppError(
            message="Refresh token has been revoked",
            status_code=401,
            code="revoked_refresh_token",
        )

    user_id = UUID(token_payload.sub)
    user = store.get_user_by_id(user_id)
    if user is None:
        raise AppError(
            message="User not found",
            status_code=401,
            code="invalid_refresh_token",
        )

    store.revoke_refresh_jti(token_payload.jti)
    return _issue_tokens(settings=settings, user=user)


@router.post("/logout")
async def logout(payload: LogoutRequest) -> dict[str, str]:
    settings = get_auth_settings()
    _ensure_jwt_keys(settings)

    store = get_auth_store()
    token_payload = _decode_refresh_or_raise(settings=settings, token=payload.refresh_token)
    store.revoke_refresh_jti(token_payload.jti)

    return {"status": "logged_out"}
