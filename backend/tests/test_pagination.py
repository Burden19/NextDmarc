import pytest
from app.repositories.pagination import build_offset_limit


def test_build_offset_limit_computes_expected_values() -> None:
    offset, limit = build_offset_limit(page=3, page_size=25)

    assert offset == 50
    assert limit == 25


def test_build_offset_limit_rejects_invalid_page() -> None:
    with pytest.raises(ValueError):
        build_offset_limit(page=0, page_size=10)


def test_build_offset_limit_rejects_invalid_page_size() -> None:
    with pytest.raises(ValueError):
        build_offset_limit(page=1, page_size=0)
