from collections import defaultdict
from datetime import UTC, datetime

from app.repositories.record_repository import RecordRepository


class SourceIntelligenceService:
    def __init__(self, *, record_repository: RecordRepository | None = None) -> None:
        self._record_repository = record_repository or RecordRepository()

    async def list_sources(self, *, tenant_id: str) -> list[dict[str, object]]:
        records = await self._all_records(tenant_id=tenant_id)
        grouped: dict[str, dict[str, object]] = {}

        for item in records:
            nested = _record(item)
            source_ip = str(nested.get("source_ip", "")).strip()
            if not source_ip:
                continue
            count = int(nested.get("count", 1))

            current = grouped.get(source_ip)
            if current is None:
                current = {
                    "source_ip": source_ip,
                    "message_count": 0,
                    "reports_count": 0,
                    "first_seen": _iso_utc_now(),
                    "last_seen": _iso_utc_now(),
                }
                grouped[source_ip] = current

            current["message_count"] = int(current["message_count"]) + count
            current["reports_count"] = int(current["reports_count"]) + 1

        return sorted(
            grouped.values(),
            key=lambda item: int(item["message_count"]),
            reverse=True,
        )

    async def get_source_detail(
        self,
        *,
        tenant_id: str,
        source_ip: str,
    ) -> dict[str, object] | None:
        records = await self.records_for_source(tenant_id=tenant_id, source_ip=source_ip)
        if not records:
            return None

        message_count = 0
        unique_domains: set[str] = set()
        dkim_failures = 0
        spf_failures = 0

        for item in records:
            nested = _record(item)
            message_count += int(nested.get("count", 1))
            header_from = str(nested.get("header_from", "")).strip().lower()
            if header_from:
                unique_domains.add(header_from)
            if str(nested.get("dkim", "pass")).lower() != "pass":
                dkim_failures += 1
            if str(nested.get("spf", "pass")).lower() != "pass":
                spf_failures += 1

        return {
            "source_ip": source_ip,
            "message_count": message_count,
            "records_count": len(records),
            "unique_domains": sorted(unique_domains),
            "dkim_failures": dkim_failures,
            "spf_failures": spf_failures,
        }

    async def source_history(self, *, tenant_id: str, source_ip: str) -> list[dict[str, object]]:
        records = await self.records_for_source(tenant_id=tenant_id, source_ip=source_ip)
        by_domain: dict[str, int] = defaultdict(int)
        for item in records:
            nested = _record(item)
            domain = str(nested.get("header_from", "unknown")).strip().lower() or "unknown"
            by_domain[domain] += int(nested.get("count", 1))

        return [
            {
                "bucket": domain,
                "message_count": count,
            }
            for domain, count in sorted(by_domain.items(), key=lambda pair: pair[1], reverse=True)
        ]

    async def records_for_source(
        self,
        *,
        tenant_id: str,
        source_ip: str,
        page: int = 1,
        page_size: int = 200,
    ) -> list[dict[str, object]]:
        results = await self._record_repository.search(
            tenant_id=tenant_id,
            query=f'record.source_ip:"{source_ip}"',
            page=page,
            page_size=page_size,
        )
        return results.items

    async def _all_records(self, *, tenant_id: str) -> list[dict[str, object]]:
        results = await self._record_repository.search(
            tenant_id=tenant_id,
            query="*",
            page=1,
            page_size=10_000,
        )
        return results.items


def _record(item: dict[str, object]) -> dict[str, object]:
    nested = item.get("record")
    if not isinstance(nested, dict):
        return {}
    return nested


def _iso_utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()
