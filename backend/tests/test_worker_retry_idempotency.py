from datetime import UTC, datetime

import pytest
from app.services.parser.dmarc_parser import DmarcParsedRecord, DmarcParsedReport, Provider
from app.services.parser.report_persister import ReportPersister
from app.workers.tasks import collect as collect_module
from app.workers.tasks import parse as parse_module


class _FakeResult:
    def __init__(self, value: str) -> None:
        self._value = value

    def scalar_one(self) -> str:
        return self._value


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.committed = False

    async def execute(self, statement, params):
        _ = params
        sql_text = str(statement)
        self.calls.append(sql_text)

        if "INSERT INTO domains" in sql_text:
            return _FakeResult("domain-fixed")
        if "INSERT INTO dmarc_reports" in sql_text:
            return _FakeResult("report-fixed")
        return _FakeResult("ok")

    async def commit(self) -> None:
        self.committed = True


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = exc_type
        _ = exc
        _ = tb
        return None


def _sample_report() -> DmarcParsedReport:
    return DmarcParsedReport(
        report_id="idempotency-report-1",
        provider=Provider.GOOGLE,
        provider_org_name="Google",
        provider_email="noreply-dmarc-support@google.com",
        policy_domain="example.com",
        date_range_begin=datetime(2026, 4, 1, tzinfo=UTC),
        date_range_end=datetime(2026, 4, 2, tzinfo=UTC),
        records=[
            DmarcParsedRecord(
                source_ip="203.0.113.10",
                count=1,
                disposition="none",
                dkim="pass",
                spf="pass",
                header_from="example.com",
                envelope_from=None,
                envelope_to=None,
            )
        ],
    )


def test_collect_retry_delay_is_capped() -> None:
    assert collect_module._retry_delay_seconds(0) == 10
    assert collect_module._retry_delay_seconds(3) == 80
    assert collect_module._retry_delay_seconds(8) == 300


def test_parse_retry_delay_is_capped() -> None:
    assert parse_module._retry_delay_seconds(0) == 10
    assert parse_module._retry_delay_seconds(3) == 80
    assert parse_module._retry_delay_seconds(8) == 300


@pytest.mark.asyncio
async def test_report_persister_uses_upserts_for_idempotency(monkeypatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(
        "app.services.parser.report_persister.get_session_factory",
        lambda: _FakeSessionFactory(fake_session),
    )

    persister = ReportPersister()

    first = await persister.persist_report(
        tenant_id="11111111-1111-1111-1111-111111111111",
        parsed=_sample_report(),
    )
    second = await persister.persist_report(
        tenant_id="11111111-1111-1111-1111-111111111111",
        parsed=_sample_report(),
    )

    assert first == "report-fixed"
    assert second == "report-fixed"
    assert fake_session.committed is True

    dmarc_upserts = [sql for sql in fake_session.calls if "INSERT INTO dmarc_reports" in sql]
    assert len(dmarc_upserts) == 2
    assert all("ON CONFLICT (tenant_id, report_id)" in sql for sql in dmarc_upserts)

    source_upserts = [sql for sql in fake_session.calls if "INSERT INTO sources" in sql]
    assert len(source_upserts) == 2
    assert all("ON CONFLICT (tenant_id, ip)" in sql for sql in source_upserts)
