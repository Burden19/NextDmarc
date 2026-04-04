import asyncio
from typing import Any

from celery import Task

from app.services.recommendation.engine import RecommendationEngine
from app.services.recommendation.store import RecommendationStore, get_recommendation_store
from app.workers.celery_app import celery_app


def _build_recommendation_engine() -> RecommendationEngine:
    return RecommendationEngine()


def _build_recommendation_store() -> RecommendationStore:
    return get_recommendation_store()


def _retry_delay_seconds(retry_count: int) -> int:
    return min(300, 10 * (2**retry_count))


@celery_app.task(
    bind=True,
    name="app.workers.tasks.recommend.generate_recommendations",
    max_retries=5,
)
def generate_recommendations(
    self: Task,
    **payload: Any,
) -> dict[str, int | str]:
    try:
        return asyncio.run(_generate_recommendations_async(payload=payload))
    except Exception as exc:
        countdown = _retry_delay_seconds(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


async def _generate_recommendations_async(
    *, payload: dict[str, Any]
) -> dict[str, int | str]:
    tenant_id = str(payload.get("tenant_id", ""))
    report_db_id = str(payload.get("report_db_id", ""))

    engine = _build_recommendation_engine()
    store = _build_recommendation_store()

    analyzed = engine.analyze(
        tenant_id=tenant_id,
        report_db_id=report_db_id,
        total_records=int(payload.get("total_records", 0)),
        spf_pass_count=int(payload.get("spf_pass_count", 0)),
        dkim_pass_count=int(payload.get("dkim_pass_count", 0)),
        dmarc_pass_count=int(payload.get("dmarc_pass_count", 0)),
        conformance_rate=float(payload.get("conformance_rate", 0.0)),
    )

    saved = store.upsert_current_and_append_history(
        tenant_id=analyzed.tenant_id,
        report_db_id=analyzed.report_db_id,
        maturity_score=analyzed.maturity_score,
        maturity_level=analyzed.maturity_level,
        items=analyzed.items,
    )

    return {
        "tenant_id": saved.tenant_id,
        "report_db_id": saved.report_db_id,
        "maturity_score": saved.maturity_score,
        "maturity_level": saved.maturity_level,
        "recommendations_count": len(saved.items),
    }
