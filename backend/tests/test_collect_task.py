import asyncio
from datetime import UTC, datetime
from email.message import EmailMessage
from uuid import uuid4

from app.repositories.mailbox_repository import MailboxEntity
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


class FakeMailboxRepository:
    def __init__(self, enabled_mailboxes: list[MailboxEntity]) -> None:
        self._enabled_mailboxes = enabled_mailboxes

    async def list_enabled(self) -> list[MailboxEntity]:
        return self._enabled_mailboxes


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


def _build_email_with_extensionless_xml_attachment() -> bytes:
    message = EmailMessage()
    message["Subject"] = "DMARC report"
    message["From"] = "reports@example.test"
    message["To"] = "collector@example.test"
    message.set_content("Please find attached.")
    message.add_attachment(
        b"<feedback/>",
        maintype="application",
        subtype="xml",
        filename="report",
    )
    return message.as_bytes()


def _build_email_with_inline_xml_body() -> bytes:
    message = EmailMessage()
    message["Subject"] = "DMARC report"
    message["From"] = "reports@example.test"
    message["To"] = "collector@example.test"
    message.set_content("<feedback/>", subtype="xml")
    return message.as_bytes()


def _build_email_with_text_plain_xml_body() -> bytes:
    message = EmailMessage()
    message["Subject"] = "DMARC report"
    message["From"] = "reports@example.test"
    message["To"] = "collector@example.test"
    message.set_content("<feedback/>", subtype="plain")
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
    queued_parse_objects: list[str] = []
    monkeypatch.setattr(
        collect_module,
        "_queue_parse_task",
        lambda *, tenant_id, object_name: queued_parse_objects.append(object_name),
    )

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
    assert queued_parse_objects == fake_uploader.objects


def test_collect_task_skips_when_run_is_already_active(monkeypatch) -> None:
    fake_redis = FakeRedis()
    fake_uploader = FakeUploader()
    fake_imap = FakeImapClient(messages=[])

    existing_lock_key = "collect:run:tenant-1:mailbox-1"
    fake_redis._values.add(existing_lock_key)

    monkeypatch.setattr(collect_module, "_build_redis_client", lambda: fake_redis)
    monkeypatch.setattr(collect_module, "_build_imap_client", lambda: fake_imap)
    monkeypatch.setattr(collect_module, "_build_uploader", lambda: fake_uploader)
    queued_parse_objects: list[str] = []
    monkeypatch.setattr(
        collect_module,
        "_queue_parse_task",
        lambda *, tenant_id, object_name: queued_parse_objects.append(object_name),
    )

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
    assert queued_parse_objects == []


def test_poll_active_mailboxes_passes_server_to_collect_task(monkeypatch) -> None:
    now = datetime.now(tz=UTC)
    mailbox = MailboxEntity(
        id=uuid4(),
        tenant_id=uuid4(),
        name="Primary",
        username="collector@example.test",
        password="secret",
        server="imap.example.test:993",
        mailbox="INBOX",
        enabled=True,
        created_at=now,
        updated_at=now,
    )

    mailbox_repository = FakeMailboxRepository(enabled_mailboxes=[mailbox])
    monkeypatch.setattr(collect_module, "get_mailbox_repository", lambda: mailbox_repository)

    calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        collect_module.collect_mailbox_reports,
        "delay",
        lambda **kwargs: calls.append(kwargs),
    )

    result = collect_module.poll_active_mailboxes()

    assert result == {"queued_mailboxes": 1}
    assert len(calls) == 1
    assert calls[0]["mailbox_id"] == str(mailbox.id)
    assert calls[0]["server"] == "imap.example.test:993"


def test_collect_task_queues_parse_for_xml_content_without_xml_extension(monkeypatch) -> None:
    raw_message = _build_email_with_extensionless_xml_attachment()
    fake_redis = FakeRedis()
    fake_uploader = FakeUploader()
    fake_imap = FakeImapClient(messages=[ImapMessage(uid="101", raw_message=raw_message)])

    monkeypatch.setattr(collect_module, "_build_redis_client", lambda: fake_redis)
    monkeypatch.setattr(collect_module, "_build_imap_client", lambda: fake_imap)
    monkeypatch.setattr(collect_module, "_build_uploader", lambda: fake_uploader)
    queued_parse_objects: list[str] = []
    monkeypatch.setattr(
        collect_module,
        "_queue_parse_task",
        lambda *, tenant_id, object_name: queued_parse_objects.append(object_name),
    )

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
        "fetched_messages": 1,
        "processed_messages": 1,
        "skipped_messages": 0,
        "uploaded_objects": 1,
        "already_running": 0,
    }
    assert queued_parse_objects == fake_uploader.objects


def test_collect_task_extracts_inline_xml_body_when_no_attachments(monkeypatch) -> None:
    raw_message = _build_email_with_inline_xml_body()
    fake_redis = FakeRedis()
    fake_uploader = FakeUploader()
    fake_imap = FakeImapClient(messages=[ImapMessage(uid="102", raw_message=raw_message)])

    monkeypatch.setattr(collect_module, "_build_redis_client", lambda: fake_redis)
    monkeypatch.setattr(collect_module, "_build_imap_client", lambda: fake_imap)
    monkeypatch.setattr(collect_module, "_build_uploader", lambda: fake_uploader)
    queued_parse_objects: list[str] = []
    monkeypatch.setattr(
        collect_module,
        "_queue_parse_task",
        lambda *, tenant_id, object_name: queued_parse_objects.append(object_name),
    )

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
        "fetched_messages": 1,
        "processed_messages": 1,
        "skipped_messages": 0,
        "uploaded_objects": 1,
        "already_running": 0,
    }
    assert queued_parse_objects == fake_uploader.objects


def test_collect_task_extracts_text_plain_xml_body_when_no_attachments(monkeypatch) -> None:
    raw_message = _build_email_with_text_plain_xml_body()
    fake_redis = FakeRedis()
    fake_uploader = FakeUploader()
    fake_imap = FakeImapClient(messages=[ImapMessage(uid="103", raw_message=raw_message)])

    monkeypatch.setattr(collect_module, "_build_redis_client", lambda: fake_redis)
    monkeypatch.setattr(collect_module, "_build_imap_client", lambda: fake_imap)
    monkeypatch.setattr(collect_module, "_build_uploader", lambda: fake_uploader)
    queued_parse_objects: list[str] = []
    monkeypatch.setattr(
        collect_module,
        "_queue_parse_task",
        lambda *, tenant_id, object_name: queued_parse_objects.append(object_name),
    )

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
        "fetched_messages": 1,
        "processed_messages": 1,
        "skipped_messages": 0,
        "uploaded_objects": 1,
        "already_running": 0,
    }
    assert queued_parse_objects == fake_uploader.objects
