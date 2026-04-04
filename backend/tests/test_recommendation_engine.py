from app.services.recommendation.engine import RecommendationEngine


def test_recommendation_engine_emits_guidance_for_low_posture() -> None:
    engine = RecommendationEngine()

    result = engine.analyze(
        tenant_id="tenant-1",
        report_db_id="report-1",
        total_records=100,
        spf_pass_count=60,
        dkim_pass_count=70,
        dmarc_pass_count=55,
        conformance_rate=0.55,
    )

    assert result.maturity_score < 70
    assert result.maturity_level in {"foundational", "developing"}
    codes = {item.code for item in result.items}
    assert "spf_alignment_hardening" in codes
    assert "dkim_key_rotation_and_alignment" in codes
    assert "dmarc_policy_progression" in codes
