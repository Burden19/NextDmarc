import asyncio
from email.message import EmailMessage
from pathlib import Path

from app.services.collector.imap_client import ImapMessage
from app.services.parser.dmarc_parser import DmarcParser
from app.workers.tasks import collect as collect_module
from app.workers.tasks import parse as parse_module
from pytest import MonkeyPatch

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "dmarc"


class FakeRedis:
    def __init__(self) -> None:
        self.values: set[str] = set()

    def set(self, key: str, value: str, nx: bool, ex: int) -> bool | None:
        _ = value
        _ = ex
        if nx and key in self.values:
            return None
        self.values.add(key)
        return True

    def delete(self, key: str) -> int:
        if key in self.values:
            self.values.remove(key)
            return 1
        return 0


class FakeImapClient:
    def __init__(self, raw_message: bytes) -> None:
        self.raw_message = raw_message

    async def fetch_unseen_messages(self, *, username: str, password: str, mailbox: str):
        _ = username
        _ = password
        _ = mailbox
        return [ImapMessage(uid="fixture-100", raw_message=self.raw_message)]


class FakeObjectStore:
    def __init__(self) -> None:
        self.payloads: dict[str, bytes] = {}


class FakeUploader:
    def __init__(self, object_store: FakeObjectStore) -> None:
        self.object_store = object_store

    async def upload_bytes(self, *, object_name: str, payload: bytes, content_type: str) -> str:
        _ = content_type
        self.object_store.payloads[object_name] = payload
        return f"s3://dmarc-raw-reports/{object_name}"


class FakeReader:
    def __init__(self, object_store: FakeObjectStore) -> None:
        self.object_store = object_store

    async def read_bytes(self, *, object_name: str) -> bytes:
        return self.object_store.payloads[object_name]


class FakePersister:
    async def persist_report(self, *, tenant_id: str, parsed) -> str:
        _ = tenant_id
        _ = parsed
        return "report-db-fixture"


class FakeIndexer:
    async def index_report(
        self,
        *,
        tenant_id: str,
        report_db_id: str,
        object_name: str,
        parsed,
    ) -> int:
        _ = tenant_id
        _ = report_db_id
        _ = object_name
        return len(parsed.records)


def _build_message_with_xml_attachment(xml_payload: bytes, filename: str) -> bytes:
    message = EmailMessage()
    message["Subject"] = "DMARC"
    message["From"] = "reports@example.test"
    message["To"] = "collector@example.test"
    message.set_content("attached")
    message.add_attachment(
        xml_payload,
        maintype="application",
        subtype="xml",
        filename=filename,
    )
    return message.as_bytes()


def _run_fixture_pipeline(*, monkeypatch: MonkeyPatch, fixture_name: str) -> dict[str, int | str]:
    object_store = FakeObjectStore()
    fake_redis = FakeRedis()
    fixture_path = FIXTURES_DIR / fixture_name

    xml_payload = fixture_path.read_bytes()

    monkeypatch.setattr(collect_module, "_build_redis_client", lambda: fake_redis)
    monkeypatch.setattr(
        collect_module,
        "_build_imap_client",
        lambda: FakeImapClient(_build_message_with_xml_attachment(xml_payload, fixture_name)),
    )
    monkeypatch.setattr(collect_module, "_build_uploader", lambda: FakeUploader(object_store))

    collect_result = asyncio.run(
        collect_module._collect_mailbox_reports_async(
            tenant_id="tenant-fixture-1",
            mailbox_id="mailbox-fixture-1",
            username="collector@example.test",
            password="secret",
            mailbox="INBOX",
        )
    )

    assert collect_result["fetched_messages"] == 1
    assert collect_result["uploaded_objects"] == 1

    object_name = next(iter(object_store.payloads.keys()))
    monkeypatch.setattr(parse_module, "_build_report_reader", lambda: FakeReader(object_store))
    monkeypatch.setattr(
        parse_module,
        "_build_dmarc_parser",
        lambda: DmarcParser(validate_schema=True),
    )
    monkeypatch.setattr(parse_module, "_build_report_persister", lambda: FakePersister())
    monkeypatch.setattr(parse_module, "_build_report_indexer", lambda: FakeIndexer())

    return asyncio.run(
        parse_module._parse_report_object_async(
            tenant_id="tenant-fixture-1",
            object_name=object_name,
        )
    )


def test_e2e_google_fixture_collect_parse_flow(monkeypatch: MonkeyPatch) -> None:
    parse_result = _run_fixture_pipeline(
        monkeypatch=monkeypatch,
        fixture_name="google-aggregate.xml",
    )

    assert parse_result["report_id"] == "google-2026-04-06-example.com"
    assert parse_result["record_count"] == 1
    assert parse_result["indexed_count"] == 1


def test_e2e_microsoft_fixture_collect_parse_flow(monkeypatch: MonkeyPatch) -> None:
    parse_result = _run_fixture_pipeline(
        monkeypatch=monkeypatch,
        fixture_name="microsoft-aggregate.xml",
    )

    assert parse_result["report_id"] == "msft-2026-04-06-example.com"
    assert parse_result["record_count"] == 1
    assert parse_result["indexed_count"] == 1
