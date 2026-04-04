import asyncio

from app.services.scoring.store import get_score_store, reset_score_store_for_tests
from app.workers.tasks.score import _compute_score_async


def test_compute_score_task_persists_current_and_history() -> None:
    reset_score_store_for_tests()
    store = get_score_store()

    payload = {
        "tenant_id": "tenant-score-1",
        "total_records": 120,
        "dkim_pass_count": 110,
        "spf_pass_count": 112,
        "dmarc_pass_count": 108,
        "conformance_rate": 0.9,
        "signals_detected": 1,
        "incidents_created": 0,
    }

    first = asyncio.run(_compute_score_async(payload=payload))
    second = asyncio.run(
        _compute_score_async(
            payload={
                **payload,
                "conformance_rate": 0.8,
                "signals_detected": 2,
                "incidents_created": 1,
            }
        )
    )

    assert first["tenant_id"] == "tenant-score-1"
    assert second["history_size"] == 2

    current = store.get_current(tenant_id="tenant-score-1")
    assert current is not None
    assert isinstance(current.score, int)
    assert current.risk_state
