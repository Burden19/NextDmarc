from dataclasses import dataclass

from app.services.correlation.detector import CorrelationSignal


@dataclass(slots=True)
class CorrelationClassification:
    signal: CorrelationSignal
    severity: str
    message: str


class CorrelationClassifier:
    def classify(self, signals: list[CorrelationSignal]) -> list[CorrelationClassification]:
        classifications: list[CorrelationClassification] = []
        for signal in signals:
            if signal.signal_type == "cross_domain_spoofing":
                severity = "critical"
            elif signal.signal_type == "volume_anomaly":
                severity = "high"
            elif signal.signal_type == "repeated_failures":
                severity = "high"
            else:
                severity = "medium"

            message = self._build_message(signal)
            classifications.append(
                CorrelationClassification(signal=signal, severity=severity, message=message)
            )

        return classifications

    def _build_message(self, signal: CorrelationSignal) -> str:
        if signal.signal_type == "repeated_failures":
            count = signal.details.get("failure_count", 0)
            return f"Repeated SPF+DKIM failures detected from {signal.source_ip} ({count} events)."
        if signal.signal_type == "new_source":
            return f"New sending source detected: {signal.source_ip}."
        if signal.signal_type == "cross_domain_spoofing":
            header_from = signal.details.get("header_from", "unknown")
            policy_domain = signal.details.get("policy_domain", "unknown")
            return (
                f"Cross-domain spoofing signal: header_from={header_from}, "
                f"policy_domain={policy_domain}."
            )
        if signal.signal_type == "volume_anomaly":
            total = signal.details.get("total_records", 0)
            return f"Volume anomaly detected with {total} records in current window."
        return "Correlation signal detected."
