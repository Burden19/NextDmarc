from app.services.correlation.detector import CorrelationDetector


def test_correlation_detector_emits_expected_signals() -> None:
    detector = CorrelationDetector(
        repeated_failure_threshold=5,
        volume_anomaly_threshold=10,
        known_sources={"203.0.113.5"},
    )

    records = [
        {
            "policy_domain": "example.com",
            "record": {
                "source_ip": "198.51.100.1",
                "count": 6,
                "dkim": "fail",
                "spf": "fail",
                "header_from": "example.com",
            },
        },
        {
            "policy_domain": "example.com",
            "record": {
                "source_ip": "203.0.113.5",
                "count": 2,
                "dkim": "pass",
                "spf": "pass",
                "header_from": "spoofed.test",
            },
        },
    ]

    signals = detector.detect(records=records, policy_domain="example.com", total_records=20)
    signal_types = {item.signal_type for item in signals}

    assert "repeated_failures" in signal_types
    assert "new_source" in signal_types
    assert "cross_domain_spoofing" in signal_types
    assert "volume_anomaly" in signal_types
