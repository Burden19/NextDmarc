from datetime import UTC, datetime

import pytest
from app.services.parser.dmarc_parser import DmarcParsedRecord, DmarcParsedReport, Provider
from app.services.parser.report_persister import ReportPersister


class FakeResult:
    def __init__(self, value: str) -> None:
        self._value = value

    def scalar_one(self) -> str:
        return self._value


class FakeSession:
    def __init__(self) -> None:
        self.executions: list[tuple[str, dict[str, str | datetime]]] = []
        self.committed = False

    async def execute(self, statement, params):
        sql_text = str(statement)
        self.executions.append((sql_text, params))

        if "INSERT INTO domains" in sql_text:
            return FakeResult("domain-uuid")
        if "INSERT INTO dmarc_reports" in sql_text:
            return FakeResult("report-uuid")
        return FakeResult("ignored")

    async def commit(self) -> None:
        self.committed = True


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self) -> FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = exc_type
        _ = exc
        _ = tb
        return None


def _sample_report() -> DmarcParsedReport:
    return DmarcParsedReport(
        report_id="report-55",
        provider=Provider.OTHER,
        provider_org_name="Provider",
        provider_email="provider@example.test",
        policy_domain="example.test",
        date_range_begin=datetime(2026, 4, 1, tzinfo=UTC),
        date_range_end=datetime(2026, 4, 2, tzinfo=UTC),
        records=[
            DmarcParsedRecord(
                source_ip="198.51.100.10",
                count=5,
                disposition="none",
                dkim="pass",
                spf="fail",
                header_from="example.test",
                envelope_from=None,
                envelope_to=None,
            )
        ],
    )


@pytest.mark.asyncio
async def test_report_persister_upserts_domain_report_and_sources(monkeypatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(
        "app.services.parser.report_persister.get_session_factory",
        lambda: FakeSessionFactory(fake_session),
    )

    persister = ReportPersister()
    report_id = await persister.persist_report(
        tenant_id="9c084e4d-640e-43b4-a849-5acfd2d529c0",
        parsed=_sample_report(),
    )

    assert report_id == "report-uuid"
    assert fake_session.committed is True
    executed_sql = "\n".join(item[0] for item in fake_session.executions)
    assert "INSERT INTO domains" in executed_sql
    assert "INSERT INTO dmarc_reports" in executed_sql
    assert "INSERT INTO sources" in executed_sql
