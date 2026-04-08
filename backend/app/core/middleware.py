import logging
from hmac import compare_digest
from time import perf_counter
from typing import cast
from uuid import uuid4

from fastapi import Request
from redis import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
WRITE_LIMIT_WINDOW_SECONDS = 60
WRITE_LIMIT_MAX_PER_WINDOW = 120
AUTH_PATH_PREFIX = "/auth"
SECURITY_HEADER_CONTENT_TYPE = "X-Content-Type-Options"
SECURITY_HEADER_FRAME_OPTIONS = "X-Frame-Options"
SECURITY_HEADER_REFERRER_POLICY = "Referrer-Policy"
SECURITY_HEADER_HSTS = "Strict-Transport-Security"
_logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id

        if _csrf_protection_failed(request=request):
            _log_blocked_request(request=request, request_id=request_id, reason="csrf")
            response = Response(content="csrf_invalid", status_code=403)
            response.headers["X-Request-ID"] = request_id
            _attach_security_headers(response=response)
            return response

        if request.method in WRITE_METHODS and _is_rate_limited(request=request):
            _log_blocked_request(request=request, request_id=request_id, reason="rate_limit")
            response = Response(content="rate_limited", status_code=429)
            response.headers["X-Request-ID"] = request_id
            response.headers["Retry-After"] = str(WRITE_LIMIT_WINDOW_SECONDS)
            _attach_security_headers(response=response)
            return response

        start = perf_counter()
        response = await call_next(request)
        duration = perf_counter() - start

        if request.method in WRITE_METHODS:
            _emit_write_audit(request=request, response=response)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration:.6f}"
        _attach_security_headers(response=response)
        return response


def _is_rate_limited(*, request: Request) -> bool:
    settings = get_settings()
    tenant_id = request.headers.get("X-Tenant-ID", "unknown").strip() or "unknown"
    key = f"ratelimit:write:{tenant_id}:{request.client.host if request.client else 'unknown'}"

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        current = cast(int, client.incr(key))
        if current == 1:
            client.expire(key, WRITE_LIMIT_WINDOW_SECONDS)
        return current > WRITE_LIMIT_MAX_PER_WINDOW
    except Exception:
        return False
    finally:
        client.close()


def _csrf_protection_failed(*, request: Request) -> bool:
    if request.method not in WRITE_METHODS:
        return False

    settings = get_settings()
    if not settings.auth_cookie_enabled:
        return False

    api_prefix = settings.api_prefix.rstrip("/")
    auth_prefix = f"{api_prefix}{AUTH_PATH_PREFIX}"
    if request.url.path.startswith(auth_prefix):
        return False

    refresh_cookie = request.cookies.get(settings.auth_refresh_cookie_name)
    if not refresh_cookie:
        return False

    csrf_cookie = request.cookies.get(settings.auth_csrf_cookie_name)
    if not csrf_cookie:
        return True

    csrf_header = request.headers.get(settings.auth_csrf_header_name)
    if not csrf_header:
        return True

    return not compare_digest(csrf_cookie, csrf_header)


def _attach_security_headers(*, response: Response) -> None:
    settings = get_settings()

    response.headers[SECURITY_HEADER_CONTENT_TYPE] = "nosniff"
    response.headers[SECURITY_HEADER_FRAME_OPTIONS] = "DENY"
    response.headers[SECURITY_HEADER_REFERRER_POLICY] = "strict-origin-when-cross-origin"

    if settings.environment in {"staging", "production"}:
        response.headers[SECURITY_HEADER_HSTS] = "max-age=31536000; includeSubDomains"


def _log_blocked_request(*, request: Request, request_id: str, reason: str) -> None:
    tenant_id = request.headers.get("X-Tenant-ID", "unknown").strip() or "unknown"
    _logger.warning(
        "Blocked request",
        extra={
            "event": "request_blocked",
            "reason": reason,
            "request_id": request_id,
            "tenant_id": tenant_id,
            "method": request.method,
            "path": request.url.path,
        },
    )


def _emit_write_audit(*, request: Request, response: Response) -> None:
    settings = get_settings()
    tenant_id = request.headers.get("X-Tenant-ID", "unknown").strip() or "unknown"
    actor = request.headers.get("X-Role", "unknown").strip() or "unknown"
    request_id = getattr(request.state, "request_id", "")

    payload = {
        "event": "write_operation",
        "request_id": request_id,
        "tenant_id": tenant_id,
        "actor": actor,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
    }

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        client.rpush("audit:write_ops", str(payload))
        client.ltrim("audit:write_ops", -10_000, -1)
    except Exception:
        return
    finally:
        client.close()
