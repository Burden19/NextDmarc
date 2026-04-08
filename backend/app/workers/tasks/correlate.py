import asyncio
from typing import Any

from celery import Task

from app.repositories.record_repository import RecordRepository
from app.services.correlation.classifier import CorrelationClassifier
from app.services.correlation.detector import CorrelationDetector
from app.services.correlation.incident_creator import CreatedIncident, IncidentCreator
from app.workers.celery_app import celery_app


def _build_record_repository() -> RecordRepository:
    return RecordRepository()


def _build_detector() -> CorrelationDetector:
    return CorrelationDetector()


def _build_classifier() -> CorrelationClassifier:
    return CorrelationClassifier()


def _build_incident_creator() -> IncidentCreator:
    return IncidentCreator()


def _retry_delay_seconds(retry_count: int) -> int:
    bounded_retry = retry_count if retry_count >= 0 else 0
    delay = 10 * (2**bounded_retry)
    return 300 if delay > 300 else delay


@celery_app.task(bind=True, name="app.workers.tasks.correlate.detect_correlations", max_retries=5)
def detect_correlations(
    self: Task,
    **payload: Any,
) -> dict[str, int | float | str]:
    try:
        return asyncio.run(_detect_correlations_async(payload=payload))
    except Exception as exc:
        countdown = _retry_delay_seconds(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


async def _detect_correlations_async(
    *,
    payload: dict[str, Any],
) -> dict[str, int | float | str]:
    tenant_id = str(payload.get("tenant_id", ""))
    report_db_id = str(payload.get("report_db_id", ""))
    total_records = int(payload.get("total_records", 0))

    repository = _build_record_repository()
    detector = _build_detector()
    classifier = _build_classifier()
    incident_creator = _build_incident_creator()

    records_page = await repository.search(
        tenant_id=tenant_id,
        query=f'report_db_id:"{report_db_id}"',
        page=1,
        page_size=10_000,
    )

    policy_domain = _extract_policy_domain(records_page.items)
    signals = detector.detect(
        records=records_page.items,
        policy_domain=policy_domain,
        total_records=total_records,
    )
    classifications = classifier.classify(signals)
    created_incidents: list[CreatedIncident]
    if isinstance(incident_creator, IncidentCreator):
        created_incidents = await incident_creator.create_incidents_with_details(
            tenant_id=tenant_id,
            classifications=classifications,
        )
        incidents_created = len(created_incidents)
    else:
        created_incidents = []
        incidents_created = await incident_creator.create_incidents(
            tenant_id=tenant_id,
            classifications=classifications,
        )

    for item in created_incidents:
        celery_app.send_task(
            "app.workers.tasks.alert.dispatch_existing_alert",
            kwargs={
                "tenant_id": tenant_id,
                "alert_id": item.id,
                "source": "correlation",
            },
        )

    return {
        "tenant_id": tenant_id,
        "report_db_id": report_db_id,
        "signals_detected": len(signals),
        "incidents_created": incidents_created,
        "alerts_enqueued": len(created_incidents),
    }


def _extract_policy_domain(records: list[dict[str, Any]]) -> str | None:
    for item in records:
        domain = item.get("policy_domain")
        if domain is None:
            continue
        value = str(domain).strip().lower()
        if value:
            return value
    return None
