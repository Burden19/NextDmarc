from datetime import UTC, datetime

from app.repositories.pagination import Page
from app.services.analytics.metrics import AnalyticsService, _as_int, _record
from app.services.scoring.engine import RiskState, ScoreBreakdown
from app.services.scoring.store import ScoreEntry, ScoreStore


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
                    "record": {
                        "source_ip": "203.0.113.1",
                        "count": 5,
                        "dkim": "pass",
                        "spf": "pass",
                        "disposition": "none",
                        "header_from": "alpha.test",
                    }
                },
                {
                    "record": {
                        "source_ip": "203.0.113.2",
                        "count": 3,
                        "dkim": "fail",
                        "spf": "pass",
                        "disposition": "reject",
                        "header_from": "beta.test",
                    }
                },
                {
                    "record": {
                        "source_ip": "203.0.113.1",
                        "count": 2,
                        "dkim": "pass",
                        "spf": "fail",
                        "disposition": "pass",
                        "header_from": "",
                    }
                },
            ],
            total=3,
            page=1,
            page_size=10_000,
        )


def _seed_score_store() -> ScoreStore:
    store = ScoreStore()
    store.upsert_current_and_append_history(
        tenant_id="tenant-a",
        score=88,
        risk_state=RiskState.HEALTHY,
        breakdown=ScoreBreakdown(0.0, 0.0, 0.0, 0.0, 0.0),
    )
    store.upsert_current_and_append_history(
        tenant_id="tenant-a",
        score=72,
        risk_state=RiskState.GUARDED,
        breakdown=ScoreBreakdown(10.0, 5.0, 4.0, 3.0, 2.0),
    )
    return store


async def test_analytics_service_computes_core_metrics() -> None:
    service = AnalyticsService(
        record_repository=FakeRecordRepository(),
        score_store=_seed_score_store(),
    )

    conformance = await service.conformance(tenant_id="tenant-a")
    top_sources = await service.top_sources(tenant_id="tenant-a", limit=2)
    volume = await service.volume(tenant_id="tenant-a")
    breakdown = await service.spf_dkim_breakdown(tenant_id="tenant-a")

    assert conformance["total_messages"] == 10
    assert conformance["conformance_rate"] == 0.7
    assert conformance["dkim_pass_rate"] == 0.7
    assert conformance["spf_pass_rate"] == 0.8
    assert conformance["dmarc_pass_rate"] == 0.7

    assert top_sources["items"][0]["source_ip"] == "203.0.113.1"
    assert top_sources["items"][0]["message_count"] == 7
    assert top_sources["items"][1]["source_ip"] == "203.0.113.2"
    assert top_sources["items"][1]["message_count"] == 3

    assert volume["total_messages"] == 10
    assert volume["by_domain"][0] == {"domain": "alpha.test", "message_count": 5}
    assert volume["by_domain"][1] == {"domain": "beta.test", "message_count": 3}
    assert volume["by_domain"][2] == {"domain": "unknown", "message_count": 2}

    assert breakdown == {
        "spf_pass_dkim_pass": 5,
        "spf_pass_dkim_fail": 3,
        "spf_fail_dkim_pass": 2,
        "spf_fail_dkim_fail": 0,
    }


def test_analytics_service_risk_trend_uses_score_history() -> None:
    store = ScoreStore()
    created = datetime(2026, 4, 7, tzinfo=UTC)
    store._history["tenant-a"] = [  # noqa: SLF001 - explicit test seeding
        ScoreEntry(
            tenant_id="tenant-a",
            score=65,
            risk_state=RiskState.ELEVATED,
            breakdown=ScoreBreakdown(1.0, 2.0, 3.0, 4.0, 5.0),
            created_at=created,
        )
    ]

    service = AnalyticsService(record_repository=FakeRecordRepository(), score_store=store)
    trend = service.risk_trend(tenant_id="tenant-a")

    assert len(trend["points"]) == 1
    assert trend["points"][0]["score"] == 65
    assert trend["points"][0]["risk_state"] == RiskState.ELEVATED
    assert trend["points"][0]["at"] == created.isoformat()


def test_analytics_helpers_handle_edge_values() -> None:
    assert _record({"record": {"count": 2}}) == {"count": 2}
    assert _record({"record": "not-a-dict"}) == {}

    assert _as_int(True, default=9) == 1
    assert _as_int(7, default=9) == 7
    assert _as_int(4.9, default=9) == 4
    assert _as_int(" 12 ", default=9) == 12
    assert _as_int("", default=9) == 9
    assert _as_int("abc", default=9) == 9
