import asyncio

import pytest
from app.repositories.pagination import Page
from app.services.correlation.classifier import CorrelationClassification
from app.services.correlation.detector import CorrelationSignal
from app.services.correlation.incident_creator import CreatedIncident, IncidentCreator
from app.workers.tasks import correlate as correlate_module


class FakeRecordRepository:
    async def search(
        self,
        *,
        tenant_id: str,
        query: str,
        page: int,
        page_size: int,
    ) -> Page[dict[str, object]]:
        _ = tenant_id
        _ = query
        _ = page
        _ = page_size
        return Page(
            items=[
                {
                    "policy_domain": "example.com",
                    "record": {
                        "source_ip": "198.51.100.10",
                        "count": 7,
                        "dkim": "fail",
                        "spf": "fail",
                        "header_from": "example.com",
                        "disposition": "none",
                    },
                }
            ],
            total=1,
            page=1,
            page_size=10_000,
        )


class FakeIncidentCreator:
    async def create_incidents(self, *, tenant_id: str, classifications) -> int:
        _ = tenant_id
        return len(classifications)


class FakeIncidentCreatorWithDetails(IncidentCreator):
    async def create_incidents_with_details(
        self,
        *,
        tenant_id: str,
        classifications,
    ) -> list[CreatedIncident]:
        _ = classifications
        return [
            CreatedIncident(
                id="alert-created-1",
                tenant_id=tenant_id,
                severity="high",
                message="Volume anomaly",
            ),
            CreatedIncident(
                id="alert-created-2",
                tenant_id=tenant_id,
                severity="medium",
                message="New source",
            ),
        ]


def test_correlate_task_detects_and_creates_incidents(monkeypatch) -> None:
    monkeypatch.setattr(correlate_module, "_build_record_repository", FakeRecordRepository)
    monkeypatch.setattr(correlate_module, "_build_incident_creator", FakeIncidentCreator)

    result = asyncio.run(
        correlate_module._detect_correlations_async(
            payload={
                "tenant_id": "tenant-1",
                "report_db_id": "report-db-1",
                "total_records": 120,
            }
        )
    )

    assert result["signals_detected"] >= 2
    assert result["incidents_created"] >= 2


def test_correlate_task_enqueues_alert_dispatch_jobs(monkeypatch) -> None:
    sent_tasks: list[tuple[str, dict[str, str]]] = []

    def fake_send_task(name: str, kwargs: dict[str, str]) -> None:
        sent_tasks.append((name, kwargs))

    monkeypatch.setattr(correlate_module, "_build_record_repository", FakeRecordRepository)
    monkeypatch.setattr(
        correlate_module,
        "_build_incident_creator",
        FakeIncidentCreatorWithDetails,
    )
    monkeypatch.setattr(correlate_module.celery_app, "send_task", fake_send_task)

    result = asyncio.run(
        correlate_module._detect_correlations_async(
            payload={
                "tenant_id": "tenant-1",
                "report_db_id": "report-db-1",
                "total_records": 120,
            }
        )
    )

    assert result["incidents_created"] == 2
    assert result["alerts_enqueued"] == 2
    assert sent_tasks[0][0] == "app.workers.tasks.alert.dispatch_existing_alert"
    assert sent_tasks[0][1]["alert_id"] == "alert-created-1"


class FakeResult:
    def __init__(self, value: str) -> None:
        self._value = value

    def scalar_one(self) -> str:
        return self._value


class FakeSession:
    def __init__(self) -> None:
        self.calls = 0
        self.committed = False

    async def execute(self, statement, params):
        _ = statement
        _ = params
        self.calls += 1
        return FakeResult("ok")

    async def commit(self) -> None:
        self.committed = True


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        _ = exc_type
        _ = exc
        _ = tb


@pytest.mark.asyncio
async def test_incident_creator_persists_alerts(monkeypatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(
        "app.services.correlation.incident_creator.get_session_factory",
        lambda: FakeSessionFactory(fake_session),
    )

    creator = IncidentCreator()
    created = await creator.create_incidents(
        tenant_id="00000000-0000-0000-0000-000000000001",
        classifications=[
            CorrelationClassification(
                signal=CorrelationSignal(
                    signal_type="volume_anomaly",
                    source_ip=None,
                    details={"total_records": 100},
                ),
                severity="high",
                message="Volume anomaly",
            ),
            CorrelationClassification(
                signal=CorrelationSignal(
                    signal_type="new_source",
                    source_ip="203.0.113.10",
                    details={"source_ip": "203.0.113.10"},
                ),
                severity="medium",
                message="New source",
            ),
        ],
    )

    assert created == 2
    assert fake_session.calls == 2
    assert fake_session.committed is True
