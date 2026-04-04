from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from app.services.scoring.engine import RiskState, ScoreBreakdown


@dataclass(slots=True)
class ScoreEntry:
    tenant_id: str
    score: int
    risk_state: RiskState
    breakdown: ScoreBreakdown
    created_at: datetime


class ScoreStore:
    def __init__(self) -> None:
        self._current: dict[str, ScoreEntry] = {}
        self._history: dict[str, list[ScoreEntry]] = {}

    def get_current(self, *, tenant_id: str) -> ScoreEntry | None:
        return self._current.get(tenant_id)

    def upsert_current_and_append_history(
        self,
        *,
        tenant_id: str,
        score: int,
        risk_state: RiskState,
        breakdown: ScoreBreakdown,
    ) -> ScoreEntry:
        entry = ScoreEntry(
            tenant_id=tenant_id,
            score=score,
            risk_state=risk_state,
            breakdown=breakdown,
            created_at=datetime.now(tz=UTC),
        )
        self._current[tenant_id] = entry
        self._history.setdefault(tenant_id, []).append(entry)
        return entry

    def history(self, *, tenant_id: str) -> list[ScoreEntry]:
        return list(self._history.get(tenant_id, []))


@lru_cache(maxsize=1)
def get_score_store() -> ScoreStore:
    return ScoreStore()


def reset_score_store_for_tests() -> None:
    get_score_store.cache_clear()
