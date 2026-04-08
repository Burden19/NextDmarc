from app.services.scoring.engine import RiskState, ScoreEngine, ScoreInput


def test_score_engine_computes_penalties_and_state() -> None:
    engine = ScoreEngine()

    result = engine.compute(
        score_input=ScoreInput(
            total_records=100,
            dkim_pass_count=90,
            spf_pass_count=80,
            dmarc_pass_count=75,
            conformance_rate=0.75,
            signals_detected=2,
            incidents_created=1,
        )
    )

    assert result.score == 70
    assert result.risk_state == RiskState.GUARDED
    assert result.breakdown.conformance_penalty == 15.0
    assert result.breakdown.dkim_penalty == 1.5
    assert result.breakdown.spf_penalty == 3.0
    assert result.breakdown.correlation_penalty == 6.0
    assert result.breakdown.incident_penalty == 5.0


def test_score_engine_hysteresis_blocks_premature_upgrade_to_healthy() -> None:
    engine = ScoreEngine()

    result = engine.compute(
        score_input=ScoreInput(
            total_records=100,
            dkim_pass_count=99,
            spf_pass_count=99,
            dmarc_pass_count=99,
            conformance_rate=0.79,
        ),
        previous_score=87,
        previous_state=RiskState.GUARDED,
    )

    assert result.score == 87
    assert result.risk_state == RiskState.GUARDED


def test_score_engine_hysteresis_delays_downgrade_above_threshold() -> None:
    engine = ScoreEngine()

    result = engine.compute(
        score_input=ScoreInput(
            total_records=100,
            dkim_pass_count=100,
            spf_pass_count=100,
            dmarc_pass_count=100,
            conformance_rate=0.72,
        ),
        previous_score=83,
        previous_state=RiskState.HEALTHY,
    )

    assert result.score == 83
    assert result.risk_state == RiskState.HEALTHY


def test_score_engine_hysteresis_allows_downgrade_at_threshold() -> None:
    engine = ScoreEngine()

    result = engine.compute(
        score_input=ScoreInput(
            total_records=100,
            dkim_pass_count=100,
            spf_pass_count=100,
            dmarc_pass_count=100,
            conformance_rate=0.70,
        ),
        previous_score=82,
        previous_state=RiskState.HEALTHY,
    )

    assert result.score == 82
    assert result.risk_state == RiskState.GUARDED
