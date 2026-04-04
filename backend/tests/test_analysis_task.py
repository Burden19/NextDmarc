import asyncio

from app.repositories.pagination import Page
from app.workers.tasks import analysis as analysis_module
from pytest import MonkeyPatch


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
                {"record": {"dkim": "pass", "spf": "fail", "disposition": "none"}},
                {"record": {"dkim": "fail", "spf": "pass", "disposition": "none"}},
                {"record": {"dkim": "fail", "spf": "fail", "disposition": "none"}},
            ],
            total=3,
            page=1,
            page_size=10_000,
        )


def test_analysis_worker_computes_metrics_and_enqueues_followups(
    monkeypatch: MonkeyPatch,
) -> None:
    sent_tasks: list[tuple[str, dict[str, int | float | str]]] = []

    def fake_send_task(name: str, kwargs: dict[str, int | float | str]) -> None:
        sent_tasks.append((name, kwargs))

    monkeypatch.setattr(analysis_module, "_build_record_repository", FakeRecordRepository)
    monkeypatch.setattr(analysis_module.celery_app, "send_task", fake_send_task)

    result = asyncio.run(
        analysis_module._analyze_report_conformance_async(
            tenant_id="tenant-1",
            report_db_id="report-db-1",
        )
    )

    assert result["total_records"] == 3
    assert result["dkim_pass_count"] == 1
    assert result["spf_pass_count"] == 1
    assert result["dmarc_pass_count"] == 2
    assert result["conformance_rate"] == 0.6667

    assert sent_tasks[0][0] == "app.workers.tasks.correlate.detect_correlations"
    assert sent_tasks[1][0] == "app.workers.tasks.score.compute_score"
