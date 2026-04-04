from datetime import UTC, datetime

import pytest
from app.repositories.report_repository import ReportRepository


class FakeMappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class FakeResult:
    def __init__(self, *, scalar_value=None, mappings_rows=None) -> None:
        self._scalar_value = scalar_value
        self._mappings_rows = mappings_rows or []

    def scalar_one(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value

    def mappings(self):
        return FakeMappingsResult(self._mappings_rows)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rows = [
            {
                "id": "report-db-1",
                "tenant_id": "tenant-1",
                "domain_id": "domain-1",
                "report_id": "rid-1",
                "reporter_org": "Google",
                "date_range_begin": datetime(2026, 4, 1, tzinfo=UTC),
                "date_range_end": datetime(2026, 4, 2, tzinfo=UTC),
                "created_at": datetime(2026, 4, 2, tzinfo=UTC),
            }
        ]

    async def execute(self, statement, params):
        sql = str(statement)
        _ = params
        if "COUNT(*)" in sql:
            return FakeResult(scalar_value=1)
        if "DELETE FROM dmarc_reports" in sql:
            return FakeResult(scalar_value="report-db-1")
        if "WHERE tenant_id = :tenant_id::uuid AND id = :id::uuid" in sql:
            return FakeResult(mappings_rows=self.rows)
        return FakeResult(mappings_rows=self.rows)

    async def commit(self) -> None:
        self.committed = True


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        _ = exc_type
        _ = exc
        _ = tb


@pytest.mark.asyncio
async def test_report_repository_get_list_delete(monkeypatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(
        "app.repositories.report_repository.get_session_factory",
        lambda: FakeSessionFactory(fake_session),
    )

    repo = ReportRepository()
    found = await repo.get_by_id(tenant_id="tenant-1", report_db_id="report-db-1")
    page = await repo.list(tenant_id="tenant-1", page=1, page_size=10)
    deleted = await repo.delete(tenant_id="tenant-1", report_db_id="report-db-1")

    assert found is not None
    assert found.report_id == "rid-1"
    assert page.total == 1
    assert len(page.items) == 1
    assert deleted is True
    assert fake_session.committed is True
