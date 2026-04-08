from app.api.v1 import alerts as alerts_module
from app.main import app
from fastapi.testclient import TestClient
from pytest import MonkeyPatch, raises
from starlette.websockets import WebSocketDisconnect

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class FakeRealtimeStream:
    def __init__(self) -> None:
        self.connected = False
        self.closed = False
        self.subscribed_tenant: str | None = None
        self._emitted = False

    async def connect(self) -> None:
        self.connected = True

    async def subscribe(self, *, tenant_id: str) -> None:
        self.subscribed_tenant = tenant_id

    async def next_event(self, *, timeout_seconds: float) -> dict[str, object] | None:
        _ = timeout_seconds
        if self._emitted:
            return None
        self._emitted = True
        return {
            "type": "alert.created",
            "tenant_id": self.subscribed_tenant,
            "alert_id": "alert-1",
            "payload": {"message": "Suspicious source"},
        }

    async def close(self) -> None:
        self.closed = True


def test_alerts_websocket_streams_tenant_events(monkeypatch: MonkeyPatch) -> None:
    fake_stream = FakeRealtimeStream()
    monkeypatch.setattr(alerts_module, "_build_realtime_stream", lambda: fake_stream)

    client = TestClient(app)
    with client.websocket_connect(
        "/api/v1/alerts/ws",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    ) as websocket:
        message = websocket.receive_json()

    assert message["type"] == "alert.created"
    assert message["tenant_id"] == TEST_TENANT_ID
    assert fake_stream.connected is True
    assert fake_stream.closed is True
    assert fake_stream.subscribed_tenant == TEST_TENANT_ID


def test_alerts_websocket_accepts_tenant_query_param(monkeypatch: MonkeyPatch) -> None:
    fake_stream = FakeRealtimeStream()
    monkeypatch.setattr(alerts_module, "_build_realtime_stream", lambda: fake_stream)

    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/alerts/ws?tenant_id={TEST_TENANT_ID}") as websocket:
        message = websocket.receive_json()

    assert message["type"] == "alert.created"
    assert message["tenant_id"] == TEST_TENANT_ID
    assert fake_stream.connected is True
    assert fake_stream.closed is True


def test_alerts_websocket_rejects_invalid_tenant_header() -> None:
    client = TestClient(app)

    with raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/api/v1/alerts/ws",
            headers={"X-Tenant-ID": "not-a-uuid"},
        ):
            pass

    assert exc.value.code == 1008
