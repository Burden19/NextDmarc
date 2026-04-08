from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache


@dataclass(slots=True)
class RecommendationResolutionEntry:
    tenant_id: str
    report_db_id: str
    resolved: bool
    resolved_at: datetime | None
    comment: str | None


class RecommendationResolutionStore:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], RecommendationResolutionEntry] = {}

    def resolve(
        self,
        *,
        tenant_id: str,
        report_db_id: str,
        resolved: bool,
        comment: str | None,
    ) -> RecommendationResolutionEntry:
        entry = RecommendationResolutionEntry(
            tenant_id=tenant_id,
            report_db_id=report_db_id,
            resolved=resolved,
            resolved_at=datetime.now(tz=UTC) if resolved else None,
            comment=comment,
        )
        self._entries[(tenant_id, report_db_id)] = entry
        return entry

    def get(self, *, tenant_id: str, report_db_id: str) -> RecommendationResolutionEntry | None:
        return self._entries.get((tenant_id, report_db_id))


@lru_cache(maxsize=1)
def get_recommendation_resolution_store() -> RecommendationResolutionStore:
    return RecommendationResolutionStore()


def reset_recommendation_resolution_store_for_tests() -> None:
    get_recommendation_resolution_store.cache_clear()
