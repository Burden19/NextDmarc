import asyncio

from celery import Task

from app.repositories.record_repository import RecordRepository
from app.services.analysis.alignment import AlignmentService
from app.workers.celery_app import celery_app


def _build_record_repository() -> RecordRepository:
    return RecordRepository()


def _build_alignment_service() -> AlignmentService:
    return AlignmentService()


def _retry_delay_seconds(retry_count: int) -> int:
    bounded_retry = retry_count if retry_count >= 0 else 0
    delay = 10 * (2**bounded_retry)
    return 300 if delay > 300 else delay


@celery_app.task(
    bind=True,
    name="app.workers.tasks.analysis.analyze_report_conformance",
    max_retries=5,
)
def analyze_report_conformance(
    self: Task,
    *,
    tenant_id: str,
    report_db_id: str,
) -> dict[str, int | float | str]:
    try:
        return asyncio.run(
            _analyze_report_conformance_async(
                tenant_id=tenant_id,
                report_db_id=report_db_id,
            )
        )
    except Exception as exc:
        countdown = _retry_delay_seconds(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


async def _analyze_report_conformance_async(
    *,
    tenant_id: str,
    report_db_id: str,
) -> dict[str, int | float | str]:
    record_repository = _build_record_repository()
    alignment_service = _build_alignment_service()

    records_page = await record_repository.search(
        tenant_id=tenant_id,
        query=f'report_db_id:"{report_db_id}"',
        page=1,
        page_size=10_000,
    )

    metrics = alignment_service.compute(records_page.items)
    payload: dict[str, int | float | str] = {
        "tenant_id": tenant_id,
        "report_db_id": report_db_id,
        "total_records": metrics.total_records,
        "dkim_pass_count": metrics.dkim_pass_count,
        "spf_pass_count": metrics.spf_pass_count,
        "dmarc_pass_count": metrics.dmarc_pass_count,
        "conformance_rate": metrics.conformance_rate,
    }

    celery_app.send_task(
        "app.workers.tasks.correlate.detect_correlations",
        kwargs=payload,
    )
    celery_app.send_task(
        "app.workers.tasks.score.compute_score",
        kwargs=payload,
    )
    celery_app.send_task(
        "app.workers.tasks.recommend.generate_recommendations",
        kwargs=payload,
    )

    return payload
