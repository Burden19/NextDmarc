from app.api.v1 import sources as sources_module
from app.main import app
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class FakeSourcesService:
    async def list_sources(self, *, tenant_id: str) -> list[dict[str, object]]:
        _ = tenant_id
        return [
            {
                "source_ip": "198.51.100.10",
                "message_count": 42,
                "reports_count": 3,
                "first_seen": "2026-04-04T00:00:00+00:00",
                "last_seen": "2026-04-04T01:00:00+00:00",
            }
        ]

    async def get_source_detail(
        self,
        *,
        tenant_id: str,
        source_ip: str,
    ) -> dict[str, object] | None:
        _ = tenant_id
        if source_ip != "198.51.100.10":
            return None
        return {
            "source_ip": source_ip,
            "message_count": 42,
            "records_count": 3,
            "unique_domains": ["example.com"],
            "dkim_failures": 1,
            "spf_failures": 2,
        }

    async def source_history(self, *, tenant_id: str, source_ip: str) -> list[dict[str, object]]:
        _ = tenant_id
        _ = source_ip
        return [{"bucket": "example.com", "message_count": 21}]

    async def records_for_source(
        self,
        *,
        tenant_id: str,
        source_ip: str,
        page: int = 1,
        page_size: int = 200,
    ) -> list[dict[str, object]]:
        _ = tenant_id
        _ = source_ip
        _ = page
        _ = page_size
        return [{"record": {"source_ip": "198.51.100.10", "count": 5}}]


def test_sources_endpoints(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sources_module, "SourceIntelligenceService", FakeSourcesService)

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    response = client.get("/api/v1/sources", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["source_ip"] == "198.51.100.10"

    detail = client.get("/api/v1/sources/198.51.100.10", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["records_count"] == 3

    history = client.get("/api/v1/sources/198.51.100.10/history", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["bucket"] == "example.com"

    records = client.get("/api/v1/sources/198.51.100.10/records", headers=headers)
    assert records.status_code == 200
    assert records.json()["items"][0]["record"]["source_ip"] == "198.51.100.10"
