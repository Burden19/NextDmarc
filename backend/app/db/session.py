from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def normalize_database_url(database_url: str) -> str:
    url = make_url(database_url)

    if url.drivername == "postgresql":
        async_url = url.set(drivername="postgresql+asyncpg")
        return async_url.render_as_string(hide_password=False)

    if url.drivername == "postgresql+asyncpg":
        return database_url

    raise ValueError("DATABASE_URL must use PostgreSQL. Example: postgresql+asyncpg://...")


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    settings = get_settings()
    database_url = normalize_database_url(settings.database_url)

    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=settings.environment == "development",
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def dispose_engine() -> None:
    await get_async_engine().dispose()


def reset_db_state_for_tests() -> None:
    get_session_factory.cache_clear()
    get_async_engine.cache_clear()
