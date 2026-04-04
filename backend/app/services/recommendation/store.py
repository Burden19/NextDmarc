from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from app.services.recommendation.models import RecommendationItem


@dataclass(slots=True)
class RecommendationEntry:
    tenant_id: str
    report_db_id: str
    maturity_score: int
    maturity_level: str
    items: list[RecommendationItem]
    created_at: datetime


class RecommendationStore:
    def __init__(self) -> None:
        self._current: dict[str, RecommendationEntry] = {}
        self._history: dict[str, list[RecommendationEntry]] = {}

    def upsert_current_and_append_history(
        self,
        *,
        tenant_id: str,
        report_db_id: str,
        maturity_score: int,
        maturity_level: str,
        items: list[RecommendationItem],
    ) -> RecommendationEntry:
        entry = RecommendationEntry(
            tenant_id=tenant_id,
            report_db_id=report_db_id,
            maturity_score=maturity_score,
            maturity_level=maturity_level,
            items=list(items),
            created_at=datetime.now(tz=UTC),
        )
        self._current[tenant_id] = entry
        self._history.setdefault(tenant_id, []).append(entry)
        return entry

    def get_current(self, *, tenant_id: str) -> RecommendationEntry | None:
        return self._current.get(tenant_id)

    def history(self, *, tenant_id: str) -> list[RecommendationEntry]:
        return list(self._history.get(tenant_id, []))


@lru_cache(maxsize=1)
def get_recommendation_store() -> RecommendationStore:
    return RecommendationStore()


def reset_recommendation_store_for_tests() -> None:
    get_recommendation_store.cache_clear()
