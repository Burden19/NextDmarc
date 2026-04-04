from fastapi import FastAPI, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.auth import router as auth_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.domains import router as domains_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.mailboxes import router as mailboxes_router
from app.api.v1.records import router as records_router
from app.api.v1.reports import router as reports_router
from app.api.v1.sources import router as sources_router
from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.middleware import RequestContextMiddleware
from app.db.session import get_async_engine


async def is_database_ready() -> bool:
    try:
        engine = get_async_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(domains_router, prefix=settings.api_prefix)
    app.include_router(mailboxes_router, prefix=settings.api_prefix)
    app.include_router(reports_router, prefix=settings.api_prefix)
    app.include_router(records_router, prefix=settings.api_prefix)
    app.include_router(sources_router, prefix=settings.api_prefix)
    app.include_router(analytics_router, prefix=settings.api_prefix)
    app.include_router(incidents_router, prefix=settings.api_prefix)

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
