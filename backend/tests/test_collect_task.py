import asyncio
from email.message import EmailMessage

from app.services.collector.imap_client import ImapMessage
from app.workers.tasks import collect as collect_module


class FakeRedis:
    def __init__(self) -> None:
        self._values: set[str] = set()

    def set(self, key: str, value: str, nx: bool, ex: int) -> bool | None:
        _ = value
        _ = ex
        if nx and key in self._values:
            return None
        self._values.add(key)
        return True

    def delete(self, key: str) -> int:
        if key in self._values:
            self._values.remove(key)
            return 1
        return 0


class FakeImapClient:
    def __init__(self, messages: list[ImapMessage]) -> None:
        self._messages = messages
        self.called = False

    async def fetch_unseen_messages(
        self,
        *,
        username: str,
        password: str,
        mailbox: str,
    ) -> list[ImapMessage]:
        _ = username
        _ = password
        _ = mailbox
        self.called = True
        return self._messages


class FakeUploader:
    def __init__(self) -> None:
        self.objects: list[str] = []

    async def upload_bytes(
        self,
        *,
        object_name: str,
        payload: bytes,
        content_type: str,
    ) -> str:
        _ = payload
        _ = content_type
        self.objects.append(object_name)
        return f"s3://dmarc-raw-reports/{object_name}"


def _build_email_with_attachment() -> bytes:
    message = EmailMessage()
    message["Subject"] = "DMARC report"
    message["From"] = "reports@example.test"
    message["To"] = "collector@example.test"
    message.set_content("Please find attached.")
    message.add_attachment(
        b"<feedback/>",
        maintype="application",
        subtype="xml",
        filename="report.xml",
    )
    return message.as_bytes()


def test_collect_task_applies_message_idempotency(monkeypatch) -> None:
    raw_message = _build_email_with_attachment()
    fake_redis = FakeRedis()
    fake_uploader = FakeUploader()
    fake_imap = FakeImapClient(
        messages=[
            ImapMessage(uid="100", raw_message=raw_message),
            ImapMessage(uid="100", raw_message=raw_message),
        ]
    )

    monkeypatch.setattr(collect_module, "_build_redis_client", lambda: fake_redis)
    monkeypatch.setattr(collect_module, "_build_imap_client", lambda: fake_imap)
    monkeypatch.setattr(collect_module, "_build_uploader", lambda: fake_uploader)

    result = asyncio.run(
        collect_module._collect_mailbox_reports_async(
            tenant_id="tenant-1",
            mailbox_id="mailbox-1",
            username="collector@example.test",
            password="secret",
            mailbox="INBOX",
        )
    )

    assert result == {
        "fetched_messages": 2,
        "processed_messages": 1,
        "skipped_messages": 1,
        "uploaded_objects": 1,
        "already_running": 0,
    }
    assert fake_imap.called is True
    assert len(fake_uploader.objects) == 1


def test_collect_task_skips_when_run_is_already_active(monkeypatch) -> None:
    fake_redis = FakeRedis()
    fake_uploader = FakeUploader()
    fake_imap = FakeImapClient(messages=[])

    existing_lock_key = "collect:run:tenant-1:mailbox-1"
    fake_redis._values.add(existing_lock_key)

    monkeypatch.setattr(collect_module, "_build_redis_client", lambda: fake_redis)
    monkeypatch.setattr(collect_module, "_build_imap_client", lambda: fake_imap)
    monkeypatch.setattr(collect_module, "_build_uploader", lambda: fake_uploader)

    result = asyncio.run(
        collect_module._collect_mailbox_reports_async(
            tenant_id="tenant-1",
            mailbox_id="mailbox-1",
            username="collector@example.test",
            password="secret",
            mailbox="INBOX",
        )
    )

    assert result == {
        "fetched_messages": 0,
        "processed_messages": 0,
        "skipped_messages": 0,
        "uploaded_objects": 0,
        "already_running": 1,
    }
    assert fake_imap.called is False
    assert fake_uploader.objects == []
