import asyncio

from celery import Task

from app.services.parser.dmarc_parser import DmarcParser
from app.services.parser.minio_report_reader import MinioReportReader
from app.services.parser.report_indexer import ReportIndexer
from app.services.parser.report_persister import ReportPersister
from app.workers.celery_app import celery_app


def _build_report_reader() -> MinioReportReader:
    return MinioReportReader()


def _build_dmarc_parser() -> DmarcParser:
    return DmarcParser(validate_schema=True)


def _build_report_persister() -> ReportPersister:
    return ReportPersister()


def _build_report_indexer() -> ReportIndexer:
    return ReportIndexer()


def _retry_delay_seconds(retry_count: int) -> int:
    bounded_retry = retry_count if retry_count >= 0 else 0
    delay = 10 * (2**bounded_retry)
    return 300 if delay > 300 else delay


@celery_app.task(bind=True, name="app.workers.tasks.parse.parse_report_object", max_retries=5)
def parse_report_object(
    self: Task,
    *,
    tenant_id: str,
    object_name: str,
) -> dict[str, int | str]:
    try:
        return asyncio.run(
            _parse_report_object_async(
                tenant_id=tenant_id,
                object_name=object_name,
            )
        )
    except Exception as exc:
        countdown = _retry_delay_seconds(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


async def _parse_report_object_async(
    *,
    tenant_id: str,
    object_name: str,
) -> dict[str, int | str]:
    reader = _build_report_reader()
    parser = _build_dmarc_parser()
    persister = _build_report_persister()
    indexer = _build_report_indexer()

    xml_payload = await reader.read_bytes(object_name=object_name)
    parsed = parser.parse(xml_payload)
    report_db_id = await persister.persist_report(tenant_id=tenant_id, parsed=parsed)
    indexed_count = await indexer.index_report(
        tenant_id=tenant_id,
        report_db_id=report_db_id,
        object_name=object_name,
        parsed=parsed,
    )

    return {
        "tenant_id": tenant_id,
        "report_id": parsed.report_id,
        "report_db_id": report_db_id,
        "record_count": len(parsed.records),
        "indexed_count": indexed_count,
    }
