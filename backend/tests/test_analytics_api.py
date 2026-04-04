from app.api.v1 import analytics as analytics_module
from app.main import app
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class FakeAnalyticsService:
    async def conformance(self, *, tenant_id: str) -> dict[str, object]:
        _ = tenant_id
        return {
            "total_messages": 100,
            "conformance_rate": 0.91,
            "dkim_pass_rate": 0.94,
            "spf_pass_rate": 0.93,
            "dmarc_pass_rate": 0.91,
        }

    def risk_trend(self, *, tenant_id: str) -> dict[str, object]:
        _ = tenant_id
        return {
            "points": [
                {
                    "at": "2026-04-04T00:00:00+00:00",
                    "score": 88,
                    "risk_state": "healthy",
                }
            ]
        }

    async def top_sources(self, *, tenant_id: str, limit: int = 10) -> dict[str, object]:
        _ = tenant_id
        _ = limit
        return {"items": [{"source_ip": "198.51.100.1", "message_count": 20}]}

    async def volume(self, *, tenant_id: str) -> dict[str, object]:
        _ = tenant_id
        return {
            "total_messages": 100,
            "by_domain": [{"domain": "example.com", "message_count": 100}],
        }

    async def spf_dkim_breakdown(self, *, tenant_id: str) -> dict[str, object]:
        _ = tenant_id
        return {
            "spf_pass_dkim_pass": 80,
            "spf_pass_dkim_fail": 10,
            "spf_fail_dkim_pass": 5,
            "spf_fail_dkim_fail": 5,
        }


def test_analytics_endpoints(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(analytics_module, "AnalyticsService", FakeAnalyticsService)

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    conformance = client.get("/api/v1/analytics/conformance", headers=headers)
    assert conformance.status_code == 200
    assert conformance.json()["conformance_rate"] == 0.91

    trend = client.get("/api/v1/analytics/risk-trend", headers=headers)
    assert trend.status_code == 200
    assert trend.json()["points"][0]["risk_state"] == "healthy"

    top_sources = client.get("/api/v1/analytics/top-sources", headers=headers)
    assert top_sources.status_code == 200
    assert top_sources.json()["items"][0]["message_count"] == 20

    volume = client.get("/api/v1/analytics/volume", headers=headers)
    assert volume.status_code == 200
    assert volume.json()["total_messages"] == 100

    breakdown = client.get("/api/v1/analytics/spf-dkim-breakdown", headers=headers)
    assert breakdown.status_code == 200
    assert breakdown.json()["spf_pass_dkim_pass"] == 80
