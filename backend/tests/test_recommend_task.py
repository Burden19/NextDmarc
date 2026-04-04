import asyncio

from app.services.recommendation.store import (
    get_recommendation_store,
    reset_recommendation_store_for_tests,
)
from app.workers.tasks.recommend import _generate_recommendations_async


def test_recommend_task_persists_current_and_history() -> None:
    reset_recommendation_store_for_tests()
    store = get_recommendation_store()

    first = asyncio.run(
        _generate_recommendations_async(
            payload={
                "tenant_id": "tenant-r-1",
                "report_db_id": "report-1",
                "total_records": 100,
                "spf_pass_count": 95,
                "dkim_pass_count": 95,
                "dmarc_pass_count": 95,
                "conformance_rate": 0.95,
            }
        )
    )
    second = asyncio.run(
        _generate_recommendations_async(
            payload={
                "tenant_id": "tenant-r-1",
                "report_db_id": "report-2",
                "total_records": 100,
                "spf_pass_count": 70,
                "dkim_pass_count": 72,
                "dmarc_pass_count": 68,
                "conformance_rate": 0.68,
            }
        )
    )

    assert first["tenant_id"] == "tenant-r-1"
    assert second["recommendations_count"] >= 1

    current = store.get_current(tenant_id="tenant-r-1")
    assert current is not None
    assert current.report_db_id == "report-2"
    assert len(store.history(tenant_id="tenant-r-1")) == 2
