from datetime import UTC, datetime
from uuid import uuid4

from app.api.v1 import mailboxes as mailbox_module
from app.main import app
from app.repositories.mailbox_repository import MailboxEntity
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


class _DelaySpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def __call__(self, **kwargs: str) -> None:
        self.calls.append(kwargs)


class _MailboxConnectionSpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def __call__(
        self,
        *,
        server: str,
        username: str,
        password: str,
        mailbox: str,
    ) -> None:
        self.calls.append(
            {
                "server": server,
                "username": username,
                "password": password,
                "mailbox": mailbox,
            }
        )


class _FakeMailboxRepository:
    def __init__(self) -> None:
        self._records: dict[str, MailboxEntity] = {}

    async def create(
        self,
        *,
        tenant_id,
        name: str,
        username: str,
        password: str,
        server: str,
        mailbox: str,
    ) -> MailboxEntity:
        now = datetime.now(tz=UTC)
        record = MailboxEntity(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            username=username,
            password=password,
            server=server,
            mailbox=mailbox,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        self._records[str(record.id)] = record
        return record

    async def list(self, *, tenant_id) -> list[MailboxEntity]:
        return [item for item in self._records.values() if item.tenant_id == tenant_id]

    async def get(self, *, tenant_id, mailbox_id) -> MailboxEntity | None:
        found = self._records.get(str(mailbox_id))
        if found is None or found.tenant_id != tenant_id:
            return None
        return found

    async def update(
        self,
        *,
        tenant_id,
        mailbox_id,
        name,
        username,
        password,
        server,
        mailbox,
        enabled,
    ) -> MailboxEntity | None:
        found = await self.get(tenant_id=tenant_id, mailbox_id=mailbox_id)
        if found is None:
            return None

        if name is not None:
            found.name = name
        if username is not None:
            found.username = username
        if password is not None:
            found.password = password
        if server is not None:
            found.server = server
        if mailbox is not None:
            found.mailbox = mailbox
        if enabled is not None:
            found.enabled = enabled
        found.updated_at = datetime.now(tz=UTC)
        return found

    async def delete(self, *, tenant_id, mailbox_id) -> bool:
        found = await self.get(tenant_id=tenant_id, mailbox_id=mailbox_id)
        if found is None:
            return False
        del self._records[str(mailbox_id)]
        return True


def test_mailboxes_crud_test_and_manual_trigger(monkeypatch: MonkeyPatch) -> None:
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}

    delay_spy = _DelaySpy()
    mailbox_connection_spy = _MailboxConnectionSpy()
    mailbox_repository = _FakeMailboxRepository()
    monkeypatch.setattr(mailbox_module.collect_mailbox_reports, "delay", delay_spy)
    monkeypatch.setattr(mailbox_module, "get_mailbox_repository", lambda: mailbox_repository)
    monkeypatch.setattr(mailbox_module, "_test_mailbox_imap_connection", mailbox_connection_spy)
    monkeypatch.setattr(mailbox_module, "_collect_workers_available", lambda: True)

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
    assert mailbox_connection_spy.calls == [
        {
            "server": "imap.example.test",
            "username": "collector@example.test",
            "password": "secret",
            "mailbox": "INBOX",
        }
    ]

    trigger_response = client.post(
        f"/api/v1/mailboxes/{mailbox_id}/trigger-collect",
        headers=headers,
    )
    assert trigger_response.status_code == 200
    assert trigger_response.json()["status"] == "queued"
    assert len(delay_spy.calls) == 1
    assert delay_spy.calls[0]["server"] == "imap.example.test"

    delete_response = client.delete(f"/api/v1/mailboxes/{mailbox_id}", headers=headers)
    assert delete_response.status_code == 204


def test_manual_trigger_returns_503_when_worker_unavailable(monkeypatch: MonkeyPatch) -> None:
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}

    mailbox_repository = _FakeMailboxRepository()
    monkeypatch.setattr(mailbox_module, "get_mailbox_repository", lambda: mailbox_repository)
    monkeypatch.setattr(mailbox_module, "_collect_workers_available", lambda: False)

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

    trigger_response = client.post(
        f"/api/v1/mailboxes/{mailbox_id}/trigger-collect",
        headers=headers,
    )
    assert trigger_response.status_code == 503
    assert trigger_response.json()["error"]["code"] == "collector_worker_unavailable"
