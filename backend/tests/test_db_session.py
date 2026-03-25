import pytest
from app.db.session import normalize_database_url


def test_normalize_database_url_adds_asyncpg_driver() -> None:
    normalized = normalize_database_url("postgresql://user:pass@localhost:5432/nextdmarc")

    assert normalized.startswith("postgresql+asyncpg://")


def test_normalize_database_url_keeps_asyncpg_driver() -> None:
    original = "postgresql+asyncpg://user:pass@localhost:5432/nextdmarc"

    assert normalize_database_url(original) == original


def test_normalize_database_url_rejects_non_postgres() -> None:
    with pytest.raises(ValueError):
        normalize_database_url("sqlite:///./local.db")
