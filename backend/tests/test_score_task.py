import asyncio

from app.services.scoring.store import get_score_store, reset_score_store_for_tests
from app.workers.tasks.score import _compute_score_async


def test_score_task_persists_current_and_history() -> None:
    reset_score_store_for_tests()
    store = get_score_store()

    first = asyncio.run(
        _compute_score_async(
            payload={
                "tenant_id": "tenant-s-1",
                "total_records": 100,
                "dkim_pass_count": 95,
                "spf_pass_count": 95,
                "dmarc_pass_count": 95,
                "conformance_rate": 0.95,
                "signals_detected": 0,
                "incidents_created": 0,
            }
        )
    )

    second = asyncio.run(
        _compute_score_async(
            payload={
                "tenant_id": "tenant-s-1",
                "total_records": 100,
                "dkim_pass_count": 72,
                "spf_pass_count": 68,
                "dmarc_pass_count": 65,
                "conformance_rate": 0.68,
                "signals_detected": 3,
                "incidents_created": 1,
            }
        )
    )

    assert first["tenant_id"] == "tenant-s-1"
    assert first["history_size"] == 1
    assert second["history_size"] == 2

    current = store.get_current(tenant_id="tenant-s-1")
    assert current is not None
    assert current.score == second["score"]
    assert current.risk_state == second["risk_state"]
    assert len(store.history(tenant_id="tenant-s-1")) == 2
