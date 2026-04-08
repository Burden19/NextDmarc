import asyncio
from typing import Any

from celery import Task

from app.services.scoring.engine import ScoreEngine, ScoreInput
from app.services.scoring.store import ScoreStore, get_score_store
from app.workers.celery_app import celery_app


def _build_score_engine() -> ScoreEngine:
    return ScoreEngine()


def _build_score_store() -> ScoreStore:
    return get_score_store()


def _retry_delay_seconds(retry_count: int) -> int:
    bounded_retry = retry_count if retry_count >= 0 else 0
    delay = 10 * (2**bounded_retry)
    return 300 if delay > 300 else delay


@celery_app.task(bind=True, name="app.workers.tasks.score.compute_score", max_retries=5)
def compute_score(
    self: Task,
    **payload: Any,
) -> dict[str, int | float | str]:
    try:
        return asyncio.run(_compute_score_async(payload=payload))
    except Exception as exc:
        countdown = _retry_delay_seconds(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


async def _compute_score_async(*, payload: dict[str, Any]) -> dict[str, int | float | str]:
    tenant_id = str(payload.get("tenant_id", ""))

    score_engine = _build_score_engine()
    score_store = _build_score_store()
    previous = score_store.get_current(tenant_id=tenant_id)

    result = score_engine.compute(
        score_input=ScoreInput(
            total_records=int(payload.get("total_records", 0)),
            dkim_pass_count=int(payload.get("dkim_pass_count", 0)),
            spf_pass_count=int(payload.get("spf_pass_count", 0)),
            dmarc_pass_count=int(payload.get("dmarc_pass_count", 0)),
            conformance_rate=float(payload.get("conformance_rate", 0.0)),
            signals_detected=int(payload.get("signals_detected", 0)),
            incidents_created=int(payload.get("incidents_created", 0)),
        ),
        previous_score=None if previous is None else previous.score,
        previous_state=None if previous is None else previous.risk_state,
    )

    stored = score_store.upsert_current_and_append_history(
        tenant_id=tenant_id,
        score=result.score,
        risk_state=result.risk_state,
        breakdown=result.breakdown,
    )

    return {
        "tenant_id": tenant_id,
        "score": stored.score,
        "risk_state": stored.risk_state,
        "history_size": len(score_store.history(tenant_id=tenant_id)),
        "conformance_penalty": stored.breakdown.conformance_penalty,
        "dkim_penalty": stored.breakdown.dkim_penalty,
        "spf_penalty": stored.breakdown.spf_penalty,
        "correlation_penalty": stored.breakdown.correlation_penalty,
        "incident_penalty": stored.breakdown.incident_penalty,
    }
