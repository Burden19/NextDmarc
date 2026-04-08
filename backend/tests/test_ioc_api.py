from app.api.v1 import ioc as ioc_module
from app.main import app
from app.repositories.pagination import Page
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


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
            items=[
                {
                    "provider": "google",
                    "policy_domain": "example.com",
                    "date_range_begin": "2026-04-04T00:00:00+00:00",
                    "date_range_end": "2026-04-04T01:00:00+00:00",
                    "record": {
                        "source_ip": "198.51.100.10",
                        "count": 10,
                        "disposition": "none",
                        "dkim": "pass",
                        "spf": "fail",
                    },
                },
                {
                    "provider": "google",
                    "policy_domain": "example.com",
                    "date_range_begin": "2026-04-04T00:00:00+00:00",
                    "date_range_end": "2026-04-04T02:00:00+00:00",
                    "record": {
                        "source_ip": "198.51.100.10",
                        "count": 5,
                        "disposition": "quarantine",
                        "dkim": "fail",
                        "spf": "pass",
                    },
                },
            ],
            total=2,
            page=1,
            page_size=10_000,
        )


def test_ioc_feed_json_and_csv(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(ioc_module, "RecordRepository", FakeRecordRepository)

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    json_response = client.get("/api/v1/ioc/json", headers=headers)
    assert json_response.status_code == 200
    payload = json_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["source_ip"] == "198.51.100.10"
    assert payload["items"][0]["message_count"] == 15

    csv_response = client.get("/api/v1/ioc/csv", headers=headers)
    assert csv_response.status_code == 200
    assert "source_ip,provider,policy_domain" in csv_response.text
    assert "198.51.100.10" in csv_response.text
