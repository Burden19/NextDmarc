import asyncio
from datetime import UTC, datetime

from app.services.parser.dmarc_parser import DmarcParsedRecord, DmarcParsedReport, Provider
from app.workers.tasks import parse as parse_module


class FakeReportReader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.requested_object_name: str | None = None

    async def read_bytes(self, *, object_name: str) -> bytes:
        self.requested_object_name = object_name
        return self.payload


class FakePersister:
    def __init__(self) -> None:
        self.last_tenant_id: str | None = None
        self.last_report: DmarcParsedReport | None = None

    async def persist_report(self, *, tenant_id: str, parsed: DmarcParsedReport) -> str:
        self.last_tenant_id = tenant_id
        self.last_report = parsed
        return "report-db-uuid"


class FakeIndexer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, DmarcParsedReport]] = []

    async def index_report(
        self,
        *,
        tenant_id: str,
        report_db_id: str,
        object_name: str,
        parsed: DmarcParsedReport,
    ) -> int:
        self.calls.append((tenant_id, report_db_id, object_name, parsed))
        return len(parsed.records)


class FakeParser:
    def __init__(self, parsed: DmarcParsedReport) -> None:
        self.parsed = parsed
        self.seen_payload: bytes | None = None

    def parse(self, xml_payload: bytes) -> DmarcParsedReport:
        self.seen_payload = xml_payload
        return self.parsed


def _sample_parsed_report() -> DmarcParsedReport:
    return DmarcParsedReport(
        report_id="report-1",
        provider=Provider.GOOGLE,
        provider_org_name="Google",
        provider_email="noreply@google.com",
        policy_domain="example.com",
        date_range_begin=datetime(2026, 4, 1, tzinfo=UTC),
        date_range_end=datetime(2026, 4, 2, tzinfo=UTC),
        records=[
            DmarcParsedRecord(
                source_ip="203.0.113.4",
                count=3,
                disposition="none",
                dkim="pass",
                spf="pass",
                header_from="example.com",
                envelope_from=None,
                envelope_to=None,
            )
        ],
    )


def test_parse_task_pipeline_reads_parses_persists_and_indexes(monkeypatch) -> None:
    parsed = _sample_parsed_report()
    reader = FakeReportReader(payload=b"<feedback/>")
    parser = FakeParser(parsed=parsed)
    persister = FakePersister()
    indexer = FakeIndexer()

    monkeypatch.setattr(parse_module, "_build_report_reader", lambda: reader)
    monkeypatch.setattr(parse_module, "_build_dmarc_parser", lambda: parser)
    monkeypatch.setattr(parse_module, "_build_report_persister", lambda: persister)
    monkeypatch.setattr(parse_module, "_build_report_indexer", lambda: indexer)

    result = asyncio.run(
        parse_module._parse_report_object_async(
            tenant_id="tenant-1",
            object_name="tenants/tenant-1/mailboxes/mbx/messages/100/001_report.xml",
        )
    )

    assert (
        reader.requested_object_name == "tenants/tenant-1/mailboxes/mbx/messages/100/001_report.xml"
    )
    assert parser.seen_payload == b"<feedback/>"
    assert persister.last_tenant_id == "tenant-1"
    assert persister.last_report is parsed
    assert len(indexer.calls) == 1
    assert result == {
        "tenant_id": "tenant-1",
        "report_id": "report-1",
        "report_db_id": "report-db-uuid",
        "record_count": 1,
        "indexed_count": 1,
    }


def test_parse_task_retry_delay_is_capped() -> None:
    assert parse_module._retry_delay_seconds(0) == 10
    assert parse_module._retry_delay_seconds(3) == 80
    assert parse_module._retry_delay_seconds(8) == 300
