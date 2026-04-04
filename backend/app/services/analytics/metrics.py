from collections import defaultdict

from app.repositories.record_repository import RecordRepository
from app.services.scoring.store import ScoreStore, get_score_store


class AnalyticsService:
    def __init__(
        self,
        *,
        record_repository: RecordRepository | None = None,
        score_store: ScoreStore | None = None,
    ) -> None:
        self._record_repository = record_repository or RecordRepository()
        self._score_store = score_store or get_score_store()

    async def conformance(self, *, tenant_id: str) -> dict[str, object]:
        records = await self._all_records(tenant_id=tenant_id)
        total = 0
        dkim_pass = 0
        spf_pass = 0
        dmarc_pass = 0

        for item in records:
            nested = _record(item)
            count = int(nested.get("count", 1))
            total += count
            if str(nested.get("dkim", "fail")).lower() == "pass":
                dkim_pass += count
            if str(nested.get("spf", "fail")).lower() == "pass":
                spf_pass += count
            if str(nested.get("disposition", "none")).lower() in {"none", "pass"}:
                dmarc_pass += count

        safe_total = max(1, total)
        conformance_rate = dmarc_pass / safe_total
        return {
            "total_messages": total,
            "conformance_rate": round(conformance_rate, 4),
            "dkim_pass_rate": round(dkim_pass / safe_total, 4),
            "spf_pass_rate": round(spf_pass / safe_total, 4),
            "dmarc_pass_rate": round(dmarc_pass / safe_total, 4),
        }

    def risk_trend(self, *, tenant_id: str) -> dict[str, object]:
        history = self._score_store.history(tenant_id=tenant_id)
        points = [
            {
                "at": item.created_at.isoformat(),
                "score": item.score,
                "risk_state": item.risk_state,
            }
            for item in history
        ]
        return {"points": points}

    async def top_sources(self, *, tenant_id: str, limit: int = 10) -> dict[str, object]:
        records = await self._all_records(tenant_id=tenant_id)
        totals: dict[str, int] = defaultdict(int)

        for item in records:
            nested = _record(item)
            source_ip = str(nested.get("source_ip", "")).strip()
            if not source_ip:
                continue
            totals[source_ip] += int(nested.get("count", 1))

        top = sorted(totals.items(), key=lambda pair: pair[1], reverse=True)[:limit]
        return {
            "items": [
                {
                    "source_ip": source_ip,
                    "message_count": count,
                }
                for source_ip, count in top
            ]
        }

    async def volume(self, *, tenant_id: str) -> dict[str, object]:
        records = await self._all_records(tenant_id=tenant_id)
        by_domain: dict[str, int] = defaultdict(int)
        total = 0

        for item in records:
            nested = _record(item)
            count = int(nested.get("count", 1))
            total += count
            domain = str(nested.get("header_from", "unknown")).strip().lower() or "unknown"
            by_domain[domain] += count

        return {
            "total_messages": total,
            "by_domain": [
                {
                    "domain": domain,
                    "message_count": count,
                }
                for domain, count in sorted(
                    by_domain.items(),
                    key=lambda pair: pair[1],
                    reverse=True,
                )
            ],
        }

    async def spf_dkim_breakdown(self, *, tenant_id: str) -> dict[str, object]:
        records = await self._all_records(tenant_id=tenant_id)
        buckets = {
            "spf_pass_dkim_pass": 0,
            "spf_pass_dkim_fail": 0,
            "spf_fail_dkim_pass": 0,
            "spf_fail_dkim_fail": 0,
        }

        for item in records:
            nested = _record(item)
            count = int(nested.get("count", 1))
            spf_pass = str(nested.get("spf", "fail")).lower() == "pass"
            dkim_pass = str(nested.get("dkim", "fail")).lower() == "pass"

            if spf_pass and dkim_pass:
                buckets["spf_pass_dkim_pass"] += count
            elif spf_pass and not dkim_pass:
                buckets["spf_pass_dkim_fail"] += count
            elif not spf_pass and dkim_pass:
                buckets["spf_fail_dkim_pass"] += count
            else:
                buckets["spf_fail_dkim_fail"] += count

        return buckets

    async def _all_records(self, *, tenant_id: str) -> list[dict[str, object]]:
        page = await self._record_repository.search(
            tenant_id=tenant_id,
            query="*",
            page=1,
            page_size=10_000,
        )
        return page.items


def _record(item: dict[str, object]) -> dict[str, object]:
    nested = item.get("record")
    if not isinstance(nested, dict):
        return {}
    return nested
