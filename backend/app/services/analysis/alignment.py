from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AlignmentRecordView:
    dkim: str
    spf: str
    disposition: str


@dataclass(slots=True)
class AlignmentMetrics:
    total_records: int
    dkim_pass_count: int
    spf_pass_count: int
    dmarc_pass_count: int
    conformance_rate: float


class AlignmentService:
    def compute(self, records: list[dict[str, Any]]) -> AlignmentMetrics:
        total = len(records)
        if total == 0:
            return AlignmentMetrics(
                total_records=0,
                dkim_pass_count=0,
                spf_pass_count=0,
                dmarc_pass_count=0,
                conformance_rate=0.0,
            )

        dkim_pass_count = 0
        spf_pass_count = 0
        dmarc_pass_count = 0

        for item in records:
            parsed = self._normalize_record(item)
            dkim_pass = parsed.dkim == "pass"
            spf_pass = parsed.spf == "pass"

            if dkim_pass:
                dkim_pass_count += 1
            if spf_pass:
                spf_pass_count += 1
            if dkim_pass or spf_pass:
                dmarc_pass_count += 1

        conformance_rate = round(dmarc_pass_count / total, 4)
        return AlignmentMetrics(
            total_records=total,
            dkim_pass_count=dkim_pass_count,
            spf_pass_count=spf_pass_count,
            dmarc_pass_count=dmarc_pass_count,
            conformance_rate=conformance_rate,
        )

    def _normalize_record(self, item: dict[str, Any]) -> AlignmentRecordView:
        nested = item.get("record", {})
        if not isinstance(nested, dict):
            nested = {}

        dkim = str(nested.get("dkim", "fail")).lower()
        spf = str(nested.get("spf", "fail")).lower()
        disposition = str(nested.get("disposition", "none")).lower()

        return AlignmentRecordView(dkim=dkim, spf=spf, disposition=disposition)
