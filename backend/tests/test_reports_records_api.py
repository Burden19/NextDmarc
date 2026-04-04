from datetime import UTC, datetime

from app.api.v1 import records as records_module
from app.api.v1 import reports as reports_module
from app.main import app
from app.repositories.pagination import Page
from app.repositories.report_repository import ReportEntity
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class FakeReportRepository:
    async def list(self, *, tenant_id: str, page: int, page_size: int) -> Page[ReportEntity]:
        _ = tenant_id
        _ = page
        _ = page_size
        return Page(
            items=[
                ReportEntity(
                    id="report-db-1",
                    tenant_id="tenant-1",
                    domain_id="domain-1",
                    report_id="rid-1",
                    reporter_org="Google",
                    date_range_begin=datetime(2026, 4, 1, tzinfo=UTC),
                    date_range_end=datetime(2026, 4, 2, tzinfo=UTC),
                    created_at=datetime(2026, 4, 2, tzinfo=UTC),
                )
            ],
            total=1,
            page=1,
            page_size=25,
        )

    async def get_by_id(self, *, tenant_id: str, report_db_id: str) -> ReportEntity | None:
        _ = tenant_id
        if report_db_id != "report-db-1":
            return None
        return ReportEntity(
            id="report-db-1",
            tenant_id="tenant-1",
            domain_id="domain-1",
            report_id="rid-1",
            reporter_org="Google",
            date_range_begin=datetime(2026, 4, 1, tzinfo=UTC),
            date_range_end=datetime(2026, 4, 2, tzinfo=UTC),
            created_at=datetime(2026, 4, 2, tzinfo=UTC),
        )


class FakeRecordRepository:
    async def search(
        self,
        *,
        tenant_id: str,
        query: str,
        page: int,
        page_size: int,
    ) -> Page[dict[str, object]]:
        _ = tenant_id
        _ = query
        _ = page
        _ = page_size
        return Page(
            items=[{"tenant_id": TEST_TENANT_ID, "record": {"source_ip": "203.0.113.1"}}],
            total=1,
            page=1,
            page_size=25,
        )

    async def get_by_id(self, *, document_id: str) -> dict[str, object] | None:
        if document_id != "doc-1":
            return None
        return {"tenant_id": TEST_TENANT_ID, "record": {"source_ip": "203.0.113.1"}}

    async def export_csv(self, *, tenant_id: str, query: str = "*") -> str:
        _ = tenant_id
        _ = query
        return "report_id,source_ip,count,dkim,spf,disposition\nrid-1,203.0.113.1,1,pass,pass,none"


def test_reports_and_records_api(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(reports_module, "ReportRepository", FakeReportRepository)
    monkeypatch.setattr(reports_module, "RecordRepository", FakeRecordRepository)
    monkeypatch.setattr(records_module, "RecordRepository", FakeRecordRepository)

    tenant_id = TEST_TENANT_ID
    headers = {"X-Tenant-ID": tenant_id}
    client = TestClient(app)

    reports_response = client.get("/api/v1/reports", headers=headers)
    assert reports_response.status_code == 200
    assert reports_response.json()["total"] == 1

    report_response = client.get("/api/v1/reports/report-db-1", headers=headers)
    assert report_response.status_code == 200
    assert report_response.json()["report_id"] == "rid-1"

    report_records = client.get("/api/v1/reports/report-db-1/records", headers=headers)
    assert report_records.status_code == 200
    assert report_records.json()["total"] == 1

    records_search = client.get("/api/v1/records", headers=headers)
    assert records_search.status_code == 200
    assert records_search.json()["total"] == 1

    record_detail = client.get("/api/v1/records/doc-1", headers=headers)
    assert record_detail.status_code == 200

    export_csv = client.get("/api/v1/records/export/csv", headers=headers)
    assert export_csv.status_code == 200
    assert "report_id,source_ip" in export_csv.text
