from app.services.scoring.engine import RiskState, ScoreEngine, ScoreInput


def test_score_engine_high_conformance_low_penalties() -> None:
    engine = ScoreEngine()

    result = engine.compute(
        score_input=ScoreInput(
            total_records=100,
            dkim_pass_count=98,
            spf_pass_count=99,
            dmarc_pass_count=97,
            conformance_rate=0.97,
            signals_detected=0,
            incidents_created=0,
        ),
        previous_score=None,
        previous_state=None,
    )

    assert result.score >= 90
    assert result.risk_state in {RiskState.HEALTHY.value, RiskState.GUARDED.value}


def test_score_engine_detects_critical_conditions() -> None:
    engine = ScoreEngine()

    result = engine.compute(
        score_input=ScoreInput(
            total_records=100,
            dkim_pass_count=10,
            spf_pass_count=15,
            dmarc_pass_count=5,
            conformance_rate=0.05,
            signals_detected=10,
            incidents_created=8,
        ),
        previous_score=None,
        previous_state=None,
    )

    assert result.score <= 30
    assert result.risk_state == RiskState.CRITICAL.value


def test_score_engine_smoothing_and_hysteresis_reduce_flapping() -> None:
    engine = ScoreEngine()

    baseline = engine.compute(
        score_input=ScoreInput(
            total_records=100,
            dkim_pass_count=95,
            spf_pass_count=96,
            dmarc_pass_count=94,
            conformance_rate=0.94,
            signals_detected=1,
            incidents_created=0,
        ),
        previous_score=None,
        previous_state=None,
    )

    # A moderate degradation should not collapse immediately due to smoothing + hysteresis.
    degraded = engine.compute(
        score_input=ScoreInput(
            total_records=100,
            dkim_pass_count=75,
            spf_pass_count=76,
            dmarc_pass_count=74,
            conformance_rate=0.74,
            signals_detected=2,
            incidents_created=1,
        ),
        previous_score=baseline.score,
        previous_state=baseline.risk_state,
    )

    assert degraded.score > 40
    assert degraded.risk_state != RiskState.CRITICAL.value
