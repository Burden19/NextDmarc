from app import main as main_module
from app.main import app
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_health_ready_returns_ready_when_database_is_available(
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_ready() -> bool:
        return True

    monkeypatch.setattr(main_module, "is_database_ready", fake_ready)

    client = TestClient(app)
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "ok"


def test_health_ready_returns_503_when_database_is_unavailable(
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_not_ready() -> bool:
        return False

    monkeypatch.setattr(main_module, "is_database_ready", fake_not_ready)

    client = TestClient(app)
    response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["database"] == "unavailable"
