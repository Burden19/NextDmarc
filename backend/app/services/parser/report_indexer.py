from elasticsearch import AsyncElasticsearch

from app.core.config import get_settings
from app.services.parser.dmarc_parser import DmarcParsedReport


class ReportIndexer:
    def __init__(self) -> None:
        settings = get_settings()
        self._index_name = settings.elasticsearch_records_index
        self._client = AsyncElasticsearch(settings.elasticsearch_url)

    async def index_report(
        self,
        *,
        tenant_id: str,
        report_db_id: str,
        object_name: str,
        parsed: DmarcParsedReport,
    ) -> int:
        await self._ensure_index_exists()

        indexed_count = 0
        for index, record in enumerate(parsed.records):
            doc_id = f"{tenant_id}:{parsed.report_id}:{index}:{record.source_ip}"
            await self._client.index(
                index=self._index_name,
                id=doc_id,
                document={
                    "tenant_id": tenant_id,
                    "report_db_id": report_db_id,
                    "report_id": parsed.report_id,
                    "object_name": object_name,
                    "provider": parsed.provider,
                    "provider_org_name": parsed.provider_org_name,
                    "provider_email": parsed.provider_email,
                    "policy_domain": parsed.policy_domain,
                    "date_range_begin": parsed.date_range_begin.isoformat(),
                    "date_range_end": parsed.date_range_end.isoformat(),
                    "record": {
                        "source_ip": record.source_ip,
                        "count": record.count,
                        "disposition": record.disposition,
                        "dkim": record.dkim,
                        "spf": record.spf,
                        "header_from": record.header_from,
                        "envelope_from": record.envelope_from,
                        "envelope_to": record.envelope_to,
                    },
                },
            )
            indexed_count += 1

        return indexed_count

    async def _ensure_index_exists(self) -> None:
        exists = await self._client.indices.exists(index=self._index_name)
        if exists:
            return
        await self._client.indices.create(index=self._index_name)
