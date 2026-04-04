from app.services.analysis.alignment import AlignmentService


def test_alignment_service_computes_conformance_metrics() -> None:
    service = AlignmentService()

    metrics = service.compute(
        [
            {"record": {"dkim": "pass", "spf": "fail", "disposition": "none"}},
            {"record": {"dkim": "fail", "spf": "pass", "disposition": "none"}},
            {"record": {"dkim": "fail", "spf": "fail", "disposition": "none"}},
        ]
    )

    assert metrics.total_records == 3
    assert metrics.dkim_pass_count == 1
    assert metrics.spf_pass_count == 1
    assert metrics.dmarc_pass_count == 2
    assert metrics.conformance_rate == 0.6667


def test_alignment_service_handles_empty_record_set() -> None:
    service = AlignmentService()

    metrics = service.compute([])

    assert metrics.total_records == 0
    assert metrics.dkim_pass_count == 0
    assert metrics.spf_pass_count == 0
    assert metrics.dmarc_pass_count == 0
    assert metrics.conformance_rate == 0.0
