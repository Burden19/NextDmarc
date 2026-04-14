import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, Protocol
from uuid import UUID, uuid4

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.rbac import Role
from app.core.security import (
    SecurityError,
    TokenPayload,
    TokenType,
    create_token,
    decode_token,
    generate_csrf_token,
    hash_password,
    verify_password,
)
from app.db.session import get_session_factory
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterTenantRequest,
    RegisterTenantResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
AUTH_RATE_LIMIT_ERROR_CODE = "auth_rate_limited"
AUTH_COOKIE_ERROR_CODE = "auth_cookie_error"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class UserRecord:
    user_id: UUID
    tenant_id: UUID
    email: str
    password_hash: str
    role: Role


class AuthStore(Protocol):
    async def register_tenant_admin(
        self,
        *,
        tenant_name: str,
        admin_email: str,
        admin_password: str,
    ) -> UserRecord: ...

    async def authenticate(self, *, tenant_id: UUID, email: str, password: str) -> UserRecord: ...

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None: ...

    async def revoke_refresh_jti(self, jti: str) -> None: ...

    async def is_refresh_revoked(self, jti: str) -> bool: ...


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _tenant_slug(tenant_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", tenant_name.strip().lower()).strip("-")
    if not normalized:
        normalized = "tenant"
    return f"{normalized}-{uuid4().hex[:12]}"


def _map_user_row(row: Mapping[str, Any]) -> UserRecord:
    role_value = str(row["role"])
    try:
        role = Role(role_value)
    except ValueError as exc:
        raise AppError(
            message="Stored user role is invalid",
            status_code=500,
            code="invalid_user_role",
        ) from exc

    return UserRecord(
        user_id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        email=str(row["email"]),
        password_hash=str(row["hashed_password"]),
        role=role,
    )


class InMemoryAuthStore(AuthStore):
    def __init__(self) -> None:
        self._users_by_scope: dict[tuple[UUID, str], UserRecord] = {}
        self._users_by_id: dict[UUID, UserRecord] = {}
        self._revoked_refresh_jti: set[str] = set()

    @staticmethod
    def _scope_key(tenant_id: UUID, email: str) -> tuple[UUID, str]:
        return (tenant_id, email.strip().lower())

    async def register_tenant_admin(
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

    async def authenticate(self, *, tenant_id: UUID, email: str, password: str) -> UserRecord:
        scope_key = self._scope_key(tenant_id, email)
        user = self._users_by_scope.get(scope_key)

        if user is None or not verify_password(password, user.password_hash):
            raise AppError(
                message="Invalid credentials",
                status_code=401,
                code="invalid_credentials",
            )

        return user

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        return self._users_by_id.get(user_id)

    async def revoke_refresh_jti(self, jti: str) -> None:
        self._revoked_refresh_jti.add(jti)

    async def is_refresh_revoked(self, jti: str) -> bool:
        return jti in self._revoked_refresh_jti


class PostgresAuthStore(AuthStore):
    def __init__(self) -> None:
        self._revoked_refresh_jti: set[str] = set()

    async def register_tenant_admin(
        self,
        *,
        tenant_name: str,
        admin_email: str,
        admin_password: str,
    ) -> UserRecord:
        tenant_id = uuid4()
        user_id = uuid4()
        normalized_email = _normalize_email(admin_email)
        slug = _tenant_slug(tenant_name)

        session_factory = get_session_factory()
        try:
            async with session_factory() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO tenants (id, name, slug, is_active, created_at, updated_at)
                        VALUES (:tenant_id, :tenant_name, :slug, true, now(), now())
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "tenant_name": tenant_name.strip(),
                        "slug": slug,
                    },
                )

                await session.execute(
                    text(
                        """
                        INSERT INTO users (
                            id,
                            tenant_id,
                            email,
                            hashed_password,
                            role,
                            is_active,
                            created_at,
                            updated_at
                        ) VALUES (
                            :user_id,
                            :tenant_id,
                            :email,
                            :hashed_password,
                            :role,
                            true,
                            now(),
                            now()
                        )
                        """
                    ),
                    {
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "email": normalized_email,
                        "hashed_password": hash_password(admin_password),
                        "role": Role.CLIENT_ADMIN.value,
                    },
                )
                await session.commit()
        except IntegrityError as exc:
            raise AppError(
                message="User already exists for this tenant",
                status_code=409,
                code="user_conflict",
            ) from exc

        return UserRecord(
            user_id=user_id,
            tenant_id=tenant_id,
            email=normalized_email,
            password_hash="",
            role=Role.CLIENT_ADMIN,
        )

    async def authenticate(self, *, tenant_id: UUID, email: str, password: str) -> UserRecord:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, email, hashed_password, role
                    FROM users
                                        WHERE tenant_id = :tenant_id
                      AND LOWER(email) = :email
                      AND is_active = true
                    LIMIT 1
                    """
                ),
                {
                                        "tenant_id": tenant_id,
                    "email": _normalize_email(email),
                },
            )
            mapped = result.mappings().first()

        if mapped is None:
            raise AppError(
                message="Invalid credentials",
                status_code=401,
                code="invalid_credentials",
            )

        user = _map_user_row(mapped)
        if not verify_password(password, user.password_hash):
            raise AppError(
                message="Invalid credentials",
                status_code=401,
                code="invalid_credentials",
            )

        return user

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, email, hashed_password, role
                    FROM users
                                        WHERE id = :user_id
                      AND is_active = true
                    LIMIT 1
                    """
                ),
                                {"user_id": user_id},
            )
            mapped = result.mappings().first()

        if mapped is None:
            return None
        return _map_user_row(mapped)

    async def revoke_refresh_jti(self, jti: str) -> None:
        self._revoked_refresh_jti.add(jti)

    async def is_refresh_revoked(self, jti: str) -> bool:
        return jti in self._revoked_refresh_jti


class AuthAttemptTracker:
    def __init__(self) -> None:
        self._login_failures: dict[str, list[datetime]] = {}
        self._login_lockouts: dict[str, datetime] = {}
        self._register_attempts: dict[str, list[datetime]] = {}
        self._register_lockouts: dict[str, datetime] = {}

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        normalized = value.strip().lower()
        return normalized or "unknown"

    @staticmethod
    def _normalize_client_ip(client_ip: str | None) -> str:
        normalized = (client_ip or "unknown").strip()
        return normalized or "unknown"

    @staticmethod
    def _remaining_seconds(*, until: datetime, now: datetime) -> int:
        return max(1, int((until - now).total_seconds()))

    @staticmethod
    def _prune_attempts(
        *,
        attempts: list[datetime],
        now: datetime,
        window_seconds: int,
    ) -> list[datetime]:
        window_start = now - timedelta(seconds=window_seconds)
        return [attempt for attempt in attempts if attempt >= window_start]

    def _consume_lockout(
        self,
        *,
        lockouts: dict[str, datetime],
        scope_key: str,
        now: datetime,
    ) -> int | None:
        lockout_until = lockouts.get(scope_key)
        if lockout_until is None:
            return None

        if lockout_until <= now:
            lockouts.pop(scope_key, None)
            return None

        return self._remaining_seconds(until=lockout_until, now=now)

    def _record_attempt(
        self,
        *,
        attempts: dict[str, list[datetime]],
        lockouts: dict[str, datetime],
        scope_key: str,
        now: datetime,
        max_attempts: int,
        window_seconds: int,
        lockout_seconds: int,
    ) -> int | None:
        active_attempts = self._prune_attempts(
            attempts=attempts.get(scope_key, []),
            now=now,
            window_seconds=window_seconds,
        )
        active_attempts.append(now)
        attempts[scope_key] = active_attempts

        if len(active_attempts) < max_attempts:
            return None

        lockouts[scope_key] = now + timedelta(seconds=lockout_seconds)
        attempts.pop(scope_key, None)
        return lockout_seconds

    def _login_scope_key(self, *, tenant_id: UUID, email: str, client_ip: str | None) -> str:
        normalized_email = self._normalize_identifier(email)
        normalized_ip = self._normalize_client_ip(client_ip)
        return f"{tenant_id}:{normalized_email}:{normalized_ip}"

    def _register_scope_key(self, *, email: str, client_ip: str | None) -> str:
        normalized_email = self._normalize_identifier(email)
        normalized_ip = self._normalize_client_ip(client_ip)
        return f"{normalized_email}:{normalized_ip}"

    def login_retry_after_seconds(
        self,
        *,
        tenant_id: UUID,
        email: str,
        client_ip: str | None,
    ) -> int | None:
        scope_key = self._login_scope_key(tenant_id=tenant_id, email=email, client_ip=client_ip)
        return self._consume_lockout(
            lockouts=self._login_lockouts,
            scope_key=scope_key,
            now=_utcnow(),
        )

    def record_login_failure(
        self,
        *,
        settings: Settings,
        tenant_id: UUID,
        email: str,
        client_ip: str | None,
    ) -> int | None:
        now = _utcnow()
        scope_key = self._login_scope_key(tenant_id=tenant_id, email=email, client_ip=client_ip)

        lockout_remaining = self._consume_lockout(
            lockouts=self._login_lockouts,
            scope_key=scope_key,
            now=now,
        )
        if lockout_remaining is not None:
            return lockout_remaining

        return self._record_attempt(
            attempts=self._login_failures,
            lockouts=self._login_lockouts,
            scope_key=scope_key,
            now=now,
            max_attempts=settings.login_max_attempts,
            window_seconds=settings.login_window_seconds,
            lockout_seconds=settings.login_lockout_seconds,
        )

    def reset_login_failures(self, *, tenant_id: UUID, email: str, client_ip: str | None) -> None:
        scope_key = self._login_scope_key(tenant_id=tenant_id, email=email, client_ip=client_ip)
        self._login_failures.pop(scope_key, None)
        self._login_lockouts.pop(scope_key, None)

    def register_retry_after_seconds(self, *, email: str, client_ip: str | None) -> int | None:
        scope_key = self._register_scope_key(email=email, client_ip=client_ip)
        return self._consume_lockout(
            lockouts=self._register_lockouts,
            scope_key=scope_key,
            now=_utcnow(),
        )

    def record_register_attempt(
        self,
        *,
        settings: Settings,
        email: str,
        client_ip: str | None,
    ) -> int | None:
        now = _utcnow()
        scope_key = self._register_scope_key(email=email, client_ip=client_ip)

        lockout_remaining = self._consume_lockout(
            lockouts=self._register_lockouts,
            scope_key=scope_key,
            now=now,
        )
        if lockout_remaining is not None:
            return lockout_remaining

        return self._record_attempt(
            attempts=self._register_attempts,
            lockouts=self._register_lockouts,
            scope_key=scope_key,
            now=now,
            max_attempts=settings.login_max_attempts,
            window_seconds=settings.login_window_seconds,
            lockout_seconds=settings.login_lockout_seconds,
        )


@lru_cache(maxsize=1)
def get_auth_store() -> AuthStore:
    settings = get_auth_settings()
    database_url = getattr(settings, "database_url", "")
    if isinstance(database_url, str) and database_url.strip():
        return PostgresAuthStore()
    return InMemoryAuthStore()


@lru_cache(maxsize=1)
def get_auth_attempt_tracker() -> AuthAttemptTracker:
    return AuthAttemptTracker()


@lru_cache(maxsize=1)
def get_auth_settings() -> Settings:
    return get_settings()


def reset_auth_store_for_tests() -> None:
    get_auth_store.cache_clear()
    get_auth_attempt_tracker.cache_clear()
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
    csrf_token = generate_csrf_token()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
    )


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


def _set_auth_cookies(*, settings: Settings, response: Response, tokens: TokenResponse) -> None:
    if not settings.auth_cookie_enabled:
        return

    cookie_domain = settings.cookie_domain or None
    refresh_cookie_max_age = settings.jwt_refresh_token_expire_days * 24 * 60 * 60

    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=refresh_cookie_max_age,
        path=settings.auth_refresh_cookie_path,
        domain=cookie_domain,
    )

    response.set_cookie(
        key=settings.auth_csrf_cookie_name,
        value=tokens.csrf_token or "",
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=refresh_cookie_max_age,
        path=settings.auth_csrf_cookie_path,
        domain=cookie_domain,
    )


def _clear_auth_cookies(*, settings: Settings, response: Response) -> None:
    if not settings.auth_cookie_enabled:
        return

    cookie_domain = settings.cookie_domain or None
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=settings.auth_refresh_cookie_path,
        domain=cookie_domain,
    )
    response.delete_cookie(
        key=settings.auth_csrf_cookie_name,
        path=settings.auth_csrf_cookie_path,
        domain=cookie_domain,
    )


def _resolve_refresh_token(
    *,
    settings: Settings,
    request: Request,
    payload_token: str | None,
) -> str:
    if payload_token and settings.auth_allow_refresh_token_body_fallback:
        return payload_token

    if payload_token and not settings.auth_allow_refresh_token_body_fallback:
        raise AppError(
            message="Refresh token body fallback is disabled",
            status_code=401,
            code=AUTH_COOKIE_ERROR_CODE,
        )

    if settings.auth_cookie_enabled:
        cookie_refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
        if cookie_refresh_token:
            return cookie_refresh_token

    raise AppError(
        message="Refresh token is missing",
        status_code=401,
        code="invalid_refresh_token",
    )


def _client_ip_from_request(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host or "unknown"


def _rate_limited_error(*, scope: str, retry_after_seconds: int) -> AppError:
    return AppError(
        message=f"Too many {scope} attempts. Retry after {retry_after_seconds} seconds.",
        status_code=429,
        code=AUTH_RATE_LIMIT_ERROR_CODE,
        details={
            "scope": scope,
            "retry_after_seconds": retry_after_seconds,
        },
    )


@router.post("/register-tenant", status_code=status.HTTP_201_CREATED)
async def register_tenant(
    payload: RegisterTenantRequest,
    request: Request,
) -> RegisterTenantResponse:
    settings = get_auth_settings()
    _ensure_jwt_keys(settings)

    tracker = get_auth_attempt_tracker()
    client_ip = _client_ip_from_request(request)

    retry_after_seconds = tracker.register_retry_after_seconds(
        email=payload.admin_email,
        client_ip=client_ip,
    )
    if retry_after_seconds is not None:
        raise _rate_limited_error(scope="register", retry_after_seconds=retry_after_seconds)

    retry_after_seconds = tracker.record_register_attempt(
        settings=settings,
        email=payload.admin_email,
        client_ip=client_ip,
    )
    if retry_after_seconds is not None:
        raise _rate_limited_error(scope="register", retry_after_seconds=retry_after_seconds)

    store = get_auth_store()
    user = await store.register_tenant_admin(
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
async def login(payload: LoginRequest, request: Request, response: Response) -> TokenResponse:
    settings = get_auth_settings()
    _ensure_jwt_keys(settings)

    tracker = get_auth_attempt_tracker()
    client_ip = _client_ip_from_request(request)
    retry_after_seconds = tracker.login_retry_after_seconds(
        tenant_id=payload.tenant_id,
        email=payload.email,
        client_ip=client_ip,
    )
    if retry_after_seconds is not None:
        raise _rate_limited_error(scope="login", retry_after_seconds=retry_after_seconds)

    store = get_auth_store()
    try:
        user = await store.authenticate(
            tenant_id=payload.tenant_id,
            email=payload.email,
            password=payload.password,
        )
    except AppError as exc:
        if exc.code != "invalid_credentials":
            raise

        retry_after_seconds = tracker.record_login_failure(
            settings=settings,
            tenant_id=payload.tenant_id,
            email=payload.email,
            client_ip=client_ip,
        )
        if retry_after_seconds is not None:
            raise _rate_limited_error(
                scope="login",
                retry_after_seconds=retry_after_seconds,
            ) from exc
        raise

    tracker.reset_login_failures(
        tenant_id=payload.tenant_id,
        email=payload.email,
        client_ip=client_ip,
    )

    tokens = _issue_tokens(settings=settings, user=user)
    _set_auth_cookies(settings=settings, response=response, tokens=tokens)
    return tokens


@router.post("/refresh")
async def refresh(payload: RefreshRequest, request: Request, response: Response) -> TokenResponse:
    settings = get_auth_settings()
    _ensure_jwt_keys(settings)

    store = get_auth_store()
    refresh_token = _resolve_refresh_token(
        settings=settings,
        request=request,
        payload_token=payload.refresh_token,
    )
    token_payload = _decode_refresh_or_raise(settings=settings, token=refresh_token)

    if await store.is_refresh_revoked(token_payload.jti):
        raise AppError(
            message="Refresh token has been revoked",
            status_code=401,
            code="revoked_refresh_token",
        )

    user_id = UUID(token_payload.sub)
    user = await store.get_user_by_id(user_id)
    if user is None:
        raise AppError(
            message="User not found",
            status_code=401,
            code="invalid_refresh_token",
        )

    await store.revoke_refresh_jti(token_payload.jti)
    tokens = _issue_tokens(settings=settings, user=user)
    _set_auth_cookies(settings=settings, response=response, tokens=tokens)
    return tokens


@router.post("/logout")
async def logout(payload: LogoutRequest, request: Request, response: Response) -> dict[str, str]:
    settings = get_auth_settings()
    _ensure_jwt_keys(settings)

    store = get_auth_store()
    refresh_token = _resolve_refresh_token(
        settings=settings,
        request=request,
        payload_token=payload.refresh_token,
    )
    token_payload = _decode_refresh_or_raise(settings=settings, token=refresh_token)
    await store.revoke_refresh_jti(token_payload.jti)
    _clear_auth_cookies(settings=settings, response=response)

    return {"status": "logged_out"}
