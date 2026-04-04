from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CorrelationSignal:
    signal_type: str
    source_ip: str | None
    details: dict[str, str | int | float]


class CorrelationDetector:
    def __init__(
        self,
        *,
        repeated_failure_threshold: int = 20,
        volume_anomaly_threshold: int = 100,
        known_sources: set[str] | None = None,
    ) -> None:
        self.repeated_failure_threshold = repeated_failure_threshold
        self.volume_anomaly_threshold = volume_anomaly_threshold
        self.known_sources = known_sources or set()

    def detect(
        self,
        *,
        records: list[dict[str, Any]],
        policy_domain: str | None,
        total_records: int,
    ) -> list[CorrelationSignal]:
        signals: list[CorrelationSignal] = []
        signals.extend(self._detect_repeated_failures(records))
        signals.extend(self._detect_new_sources(records))
        signals.extend(self._detect_cross_domain_spoofing(records, policy_domain=policy_domain))
        signals.extend(self._detect_volume_anomaly(total_records=total_records))
        return signals

    def _detect_repeated_failures(self, records: list[dict[str, Any]]) -> list[CorrelationSignal]:
        failing_by_source: dict[str, int] = defaultdict(int)
        for item in records:
            nested = _record(item)
            source_ip = str(nested.get("source_ip", "")).strip()
            if not source_ip:
                continue

            dkim = str(nested.get("dkim", "fail")).lower()
            spf = str(nested.get("spf", "fail")).lower()
            count = int(nested.get("count", 1))
            if dkim == "fail" and spf == "fail":
                failing_by_source[source_ip] += count

        signals: list[CorrelationSignal] = []
        for source_ip, failure_count in failing_by_source.items():
            if failure_count < self.repeated_failure_threshold:
                continue
            signals.append(
                CorrelationSignal(
                    signal_type="repeated_failures",
                    source_ip=source_ip,
                    details={"failure_count": failure_count},
                )
            )
        return signals

    def _detect_new_sources(self, records: list[dict[str, Any]]) -> list[CorrelationSignal]:
        signals: list[CorrelationSignal] = []
        for item in records:
            nested = _record(item)
            source_ip = str(nested.get("source_ip", "")).strip()
            if not source_ip:
                continue
            if source_ip in self.known_sources:
                continue
            signals.append(
                CorrelationSignal(
                    signal_type="new_source",
                    source_ip=source_ip,
                    details={"source_ip": source_ip},
                )
            )
        return _dedupe_signals(signals)

    def _detect_cross_domain_spoofing(
        self,
        records: list[dict[str, Any]],
        *,
        policy_domain: str | None,
    ) -> list[CorrelationSignal]:
        if policy_domain is None:
            return []

        normalized_policy = policy_domain.lower()
        signals: list[CorrelationSignal] = []
        for item in records:
            nested = _record(item)
            source_ip = str(nested.get("source_ip", "")).strip() or None
            header_from = str(nested.get("header_from", "")).lower().strip()
            if not header_from or header_from == normalized_policy:
                continue
            signals.append(
                CorrelationSignal(
                    signal_type="cross_domain_spoofing",
                    source_ip=source_ip,
                    details={
                        "header_from": header_from,
                        "policy_domain": normalized_policy,
                    },
                )
            )
        return _dedupe_signals(signals)

    def _detect_volume_anomaly(self, *, total_records: int) -> list[CorrelationSignal]:
        if total_records < self.volume_anomaly_threshold:
            return []
        return [
            CorrelationSignal(
                signal_type="volume_anomaly",
                source_ip=None,
                details={"total_records": total_records},
            )
        ]


def _record(item: dict[str, Any]) -> dict[str, Any]:
    nested = item.get("record", {})
    if not isinstance(nested, dict):
        return {}
    return nested


def _dedupe_signals(signals: list[CorrelationSignal]) -> list[CorrelationSignal]:
    seen: set[tuple[str, str | None]] = set()
    result: list[CorrelationSignal] = []
    for signal in signals:
        key = (signal.signal_type, signal.source_ip)
        if key in seen:
            continue
        seen.add(key)
        result.append(signal)
    return result
