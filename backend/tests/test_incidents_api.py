from datetime import UTC, datetime

from app.api.v1 import incidents as incidents_module
from app.main import app
from app.repositories.incident_repository import IncidentEntity
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class FakeIncidentRepository:
    async def list(self, *, tenant_id: str, limit: int = 100) -> list[IncidentEntity]:
        _ = tenant_id
        _ = limit
        return [
            IncidentEntity(
                id="incident-1",
                tenant_id=TEST_TENANT_ID,
                severity="high",
                status="new",
                message="Suspicious source",
                created_at=datetime(2026, 4, 4, tzinfo=UTC),
                updated_at=datetime(2026, 4, 4, tzinfo=UTC),
            )
        ]

    async def get_by_id(self, *, tenant_id: str, incident_id: str) -> IncidentEntity | None:
        _ = tenant_id
        if incident_id != "incident-1":
            return None
        return IncidentEntity(
            id="incident-1",
            tenant_id=TEST_TENANT_ID,
            severity="high",
            status="new",
            message="Suspicious source",
            created_at=datetime(2026, 4, 4, tzinfo=UTC),
            updated_at=datetime(2026, 4, 4, tzinfo=UTC),
        )

    async def close(self, *, tenant_id: str, incident_id: str) -> IncidentEntity | None:
        _ = tenant_id
        if incident_id != "incident-1":
            return None
        return IncidentEntity(
            id="incident-1",
            tenant_id=TEST_TENANT_ID,
            severity="high",
            status="closed",
            message="Suspicious source",
            created_at=datetime(2026, 4, 4, tzinfo=UTC),
            updated_at=datetime(2026, 4, 4, tzinfo=UTC),
        )


def test_incidents_endpoints(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(incidents_module, "IncidentRepository", FakeIncidentRepository)

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    listing = client.get("/api/v1/incidents", headers=headers)
    assert listing.status_code == 200
    assert listing.json()[0]["id"] == "incident-1"

    detail = client.get("/api/v1/incidents/incident-1", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["severity"] == "high"

    closed = client.post("/api/v1/incidents/incident-1/close", headers=headers)
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
