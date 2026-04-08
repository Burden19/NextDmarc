import sys

from fastapi import FastAPI, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.domains import router as domains_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.ioc import router as ioc_router
from app.api.v1.mailboxes import router as mailboxes_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.records import router as records_router
from app.api.v1.reports import router as reports_router
from app.api.v1.sources import router as sources_router
from app.core.config import (
    DEFAULT_DEVELOPMENT_CORS_ORIGINS,
    DEFAULT_DEVELOPMENT_TRUSTED_HOSTS,
    Settings,
    get_settings,
)
from app.core.exceptions import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.middleware import RequestContextMiddleware
from app.core.observability import (
    configure_structured_logging,
    setup_metrics,
    setup_opentelemetry,
)
from app.db.session import get_async_engine


async def is_database_ready() -> bool:
    try:
        engine = get_async_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _resolve_runtime_security_lists(settings: Settings) -> tuple[list[str], list[str]]:
    cors_origins = list(settings.cors_origins)
    trusted_hosts = list(settings.trusted_hosts)

    if settings.environment == "development":
        if not cors_origins:
            cors_origins = list(DEFAULT_DEVELOPMENT_CORS_ORIGINS)
        if not trusted_hosts:
            trusted_hosts = list(DEFAULT_DEVELOPMENT_TRUSTED_HOSTS)
        if "pytest" in sys.modules and "testserver" not in trusted_hosts:
            trusted_hosts.append("testserver")

    return cors_origins, trusted_hosts


def _validate_runtime_security_settings(
    *,
    settings: Settings,
    cors_origins: list[str],
    trusted_hosts: list[str],
) -> None:
    if settings.environment not in {"staging", "production"}:
        return

    if not cors_origins:
        raise ValueError("CORS origins must be configured in staging/production")
    if any("*" in origin for origin in cors_origins):
        raise ValueError("CORS origins cannot contain wildcard values in staging/production")
    if any(not origin.startswith("https://") for origin in cors_origins):
        raise ValueError("CORS origins must use https:// in staging/production")

    if not trusted_hosts:
        raise ValueError("Trusted hosts must be configured in staging/production")
    if any("*" in host for host in trusted_hosts):
        raise ValueError("Trusted hosts cannot contain wildcard values in staging/production")

    if not settings.cookie_secure:
        raise ValueError("cookie_secure must be enabled in staging/production")


def create_app() -> FastAPI:
    settings = get_settings()
    cors_origins, trusted_hosts = _resolve_runtime_security_lists(settings)
    _validate_runtime_security_settings(
        settings=settings,
        cors_origins=cors_origins,
        trusted_hosts=trusted_hosts,
    )

    configure_structured_logging(log_level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allowed_methods,
        allow_headers=settings.cors_allowed_headers,
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    setup_metrics(app=app, enabled=True)
    setup_opentelemetry(app=app, enabled=True)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(domains_router, prefix=settings.api_prefix)
    app.include_router(mailboxes_router, prefix=settings.api_prefix)
    app.include_router(reports_router, prefix=settings.api_prefix)
    app.include_router(records_router, prefix=settings.api_prefix)
    app.include_router(sources_router, prefix=settings.api_prefix)
    app.include_router(analytics_router, prefix=settings.api_prefix)
    app.include_router(incidents_router, prefix=settings.api_prefix)
    app.include_router(alerts_router, prefix=settings.api_prefix)
    app.include_router(integrations_router, prefix=settings.api_prefix)
    app.include_router(recommendations_router, prefix=settings.api_prefix)
    app.include_router(ioc_router, prefix=settings.api_prefix)

    @app.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "environment": settings.environment,
            "status": "ok",
        }

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.environment,
        }

    @app.get("/health/ready", tags=["system"])
    async def health_ready(response: Response) -> dict[str, str]:
        if not await is_database_ready():
            response.status_code = 503
            return {"status": "degraded", "database": "unavailable"}

        return {"status": "ready", "database": "ok"}

    return app


app = create_app()
