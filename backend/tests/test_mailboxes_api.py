from uuid import uuid4

from app.api.v1 import mailboxes as mailbox_module
from app.main import app
from app.services.mailbox_store import reset_mailbox_store_for_tests
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


class _DelaySpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def __call__(self, **kwargs: str) -> None:
        self.calls.append(kwargs)


def test_mailboxes_crud_test_and_manual_trigger(monkeypatch: MonkeyPatch) -> None:
    reset_mailbox_store_for_tests()
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}

    delay_spy = _DelaySpy()
    monkeypatch.setattr(mailbox_module.collect_mailbox_reports, "delay", delay_spy)

    client = TestClient(app)

    create_response = client.post(
        "/api/v1/mailboxes",
        headers=headers,
        json={
            "name": "Primary",
            "username": "collector@example.test",
            "password": "secret",
            "server": "imap.example.test",
            "mailbox": "INBOX",
        },
    )
    assert create_response.status_code == 201
    mailbox_id = create_response.json()["id"]

    test_response = client.post(f"/api/v1/mailboxes/{mailbox_id}/test", headers=headers)
    assert test_response.status_code == 200
    assert test_response.json()["status"] == "ok"

    trigger_response = client.post(
        f"/api/v1/mailboxes/{mailbox_id}/trigger-collect",
        headers=headers,
    )
    assert trigger_response.status_code == 200
    assert trigger_response.json()["status"] == "queued"
    assert len(delay_spy.calls) == 1

    delete_response = client.delete(f"/api/v1/mailboxes/{mailbox_id}", headers=headers)
    assert delete_response.status_code == 204
