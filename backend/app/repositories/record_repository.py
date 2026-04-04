from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.core.config import get_settings
from app.repositories.pagination import Page, build_offset_limit


class RecordRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self._index_name = settings.elasticsearch_records_index
        self._client = AsyncElasticsearch(settings.elasticsearch_url)

    async def get_by_id(self, *, document_id: str) -> dict[str, Any] | None:
        try:
            response = await self._client.get(index=self._index_name, id=document_id)
        except NotFoundError:
            return None
        source = response.get("_source", {})
        return source if isinstance(source, dict) else None

    async def search(
        self,
        *,
        tenant_id: str,
        query: str,
        page: int,
        page_size: int,
    ) -> Page[dict[str, Any]]:
        offset, limit = build_offset_limit(page=page, page_size=page_size)

        body: dict[str, Any] = {
            "query": {
                "bool": {
                    "filter": [{"term": {"tenant_id": tenant_id}}],
                    "must": [],
                }
            },
            "from": offset,
            "size": limit,
            "sort": [{"date_range_end": {"order": "desc"}}],
        }

        if query != "*":
            body["query"]["bool"]["must"].append(
                {
                    "query_string": {
                        "query": query,
                        "default_field": "record.source_ip",
                    }
                }
            )

        response = await self._client.search(index=self._index_name, body=body)
        hits = response.get("hits", {})
        total_data = hits.get("total", {})
        total = int(total_data.get("value", 0)) if isinstance(total_data, dict) else 0

        raw_hits = hits.get("hits", [])
        items: list[dict[str, Any]] = []
        for hit in raw_hits:
            if not isinstance(hit, dict):
                continue
            source = hit.get("_source", {})
            if isinstance(source, dict):
                items.append(source)

        return Page(items=items, total=total, page=page, page_size=page_size)

    async def delete(self, *, document_id: str) -> bool:
        try:
            await self._client.delete(index=self._index_name, id=document_id)
            return True
        except NotFoundError:
            return False

    async def export_csv(self, *, tenant_id: str, query: str = "*") -> str:
        page = await self.search(tenant_id=tenant_id, query=query, page=1, page_size=10_000)

        rows = ["report_id,source_ip,count,dkim,spf,disposition"]
        for item in page.items:
            record = item.get("record", {})
            if not isinstance(record, dict):
                continue
            rows.append(
                ",".join(
                    [
                        str(item.get("report_id", "")),
                        str(record.get("source_ip", "")),
                        str(record.get("count", "")),
                        str(record.get("dkim", "")),
                        str(record.get("spf", "")),
                        str(record.get("disposition", "")),
                    ]
                )
            )

        return "\n".join(rows)
