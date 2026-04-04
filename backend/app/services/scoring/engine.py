from dataclasses import dataclass
from enum import StrEnum


class RiskState(StrEnum):
    HEALTHY = "healthy"
    GUARDED = "guarded"
    ELEVATED = "elevated"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"


@dataclass(slots=True)
class ScoreInput:
    total_records: int
    dkim_pass_count: int
    spf_pass_count: int
    dmarc_pass_count: int
    conformance_rate: float
    signals_detected: int = 0
    incidents_created: int = 0


@dataclass(slots=True)
class ScoreBreakdown:
    conformance_penalty: float
    dkim_penalty: float
    spf_penalty: float
    correlation_penalty: float
    incident_penalty: float


@dataclass(slots=True)
class ScoreResult:
    score: int
    risk_state: RiskState
    breakdown: ScoreBreakdown


class ScoreEngine:
    def compute(
        self,
        *,
        score_input: ScoreInput,
        previous_score: int | None = None,
        previous_state: RiskState | None = None,
    ) -> ScoreResult:
        total = max(1, score_input.total_records)

        dkim_fail_ratio = max(0.0, 1.0 - (score_input.dkim_pass_count / total))
        spf_fail_ratio = max(0.0, 1.0 - (score_input.spf_pass_count / total))
        conformance_penalty = (1.0 - max(0.0, min(1.0, score_input.conformance_rate))) * 60.0
        dkim_penalty = dkim_fail_ratio * 15.0
        spf_penalty = spf_fail_ratio * 15.0
        correlation_penalty = min(15.0, float(score_input.signals_detected) * 3.0)
        incident_penalty = min(20.0, float(score_input.incidents_created) * 5.0)

        raw_score = 100.0 - (
            conformance_penalty
            + dkim_penalty
            + spf_penalty
            + correlation_penalty
            + incident_penalty
        )
        bounded_score = int(round(max(0.0, min(100.0, raw_score))))

        if previous_score is not None:
            smoothed = int(round((0.6 * bounded_score) + (0.4 * previous_score)))
        else:
            smoothed = bounded_score

        target_state = self._state_from_score(smoothed)
        risk_state = self._apply_hysteresis(
            score=smoothed,
            target_state=target_state,
            previous_state=previous_state,
        )

        return ScoreResult(
            score=smoothed,
            risk_state=risk_state,
            breakdown=ScoreBreakdown(
                conformance_penalty=round(conformance_penalty, 2),
                dkim_penalty=round(dkim_penalty, 2),
                spf_penalty=round(spf_penalty, 2),
                correlation_penalty=round(correlation_penalty, 2),
                incident_penalty=round(incident_penalty, 2),
            ),
        )

    def _state_from_score(self, score: int) -> RiskState:
        if score >= 85:
            return RiskState.HEALTHY
        if score >= 70:
            return RiskState.GUARDED
        if score >= 50:
            return RiskState.ELEVATED
        if score >= 30:
            return RiskState.HIGH_RISK
        return RiskState.CRITICAL

    def _apply_hysteresis(
        self,
        *,
        score: int,
        target_state: RiskState,
        previous_state: RiskState | None,
    ) -> RiskState:
        if previous_state is None or previous_state == target_state:
            return target_state

        index = {
            RiskState.CRITICAL: 0,
            RiskState.HIGH_RISK: 1,
            RiskState.ELEVATED: 2,
            RiskState.GUARDED: 3,
            RiskState.HEALTHY: 4,
        }
        previous_index = index[previous_state]
        target_index = index[target_state]

        if target_index > previous_index:
            minimum_for_upgrade = {
                RiskState.HIGH_RISK: 33,
                RiskState.ELEVATED: 53,
                RiskState.GUARDED: 73,
                RiskState.HEALTHY: 88,
                RiskState.CRITICAL: 0,
            }[target_state]
            return target_state if score >= minimum_for_upgrade else previous_state

        maximum_for_downgrade = {
            RiskState.HEALTHY: 82,
            RiskState.GUARDED: 67,
            RiskState.ELEVATED: 47,
            RiskState.HIGH_RISK: 27,
            RiskState.CRITICAL: -1,
        }[previous_state]
        return target_state if score <= maximum_for_downgrade else previous_state
