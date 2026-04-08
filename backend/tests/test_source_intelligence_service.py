from app.repositories.pagination import Page
from app.services.sources.intelligence import SourceIntelligenceService, _as_int, _record


class FakeRecordRepository:
    def __init__(self) -> None:
        self._all_items = [
            {
                "record": {
                    "source_ip": "198.51.100.1",
                    "count": 4,
                    "header_from": "alpha.test",
                    "dkim": "fail",
                    "spf": "pass",
                }
            },
            {
                "record": {
                    "source_ip": "198.51.100.1",
                    "count": "2",
                    "header_from": "beta.test",
                    "dkim": "pass",
                    "spf": "fail",
                }
            },
            {
                "record": {
                    "source_ip": "198.51.100.2",
                    "count": 1,
                    "header_from": "alpha.test",
                    "dkim": "pass",
                    "spf": "pass",
                }
            },
            {
                "record": {
                    "source_ip": "",
                    "count": 5,
                    "header_from": "ignored.test",
                }
            },
        ]

    async def search(
        self,
        *,
        tenant_id: str,
        query: str,
        page: int,
        page_size: int,
    ) -> Page[dict[str, object]]:
        _ = tenant_id
        _ = page
        _ = page_size

        if query == "*":
            items = self._all_items
        elif query == 'record.source_ip:"198.51.100.1"':
            items = self._all_items[:2]
        else:
            items = []

        return Page(items=items, total=len(items), page=1, page_size=10_000)


async def test_source_intelligence_lists_and_details_sources() -> None:
    service = SourceIntelligenceService(record_repository=FakeRecordRepository())

    listed = await service.list_sources(tenant_id="tenant-s")
    detail = await service.get_source_detail(tenant_id="tenant-s", source_ip="198.51.100.1")
    history = await service.source_history(tenant_id="tenant-s", source_ip="198.51.100.1")
    records = await service.records_for_source(tenant_id="tenant-s", source_ip="198.51.100.1")

    assert listed[0]["source_ip"] == "198.51.100.1"
    assert listed[0]["message_count"] == 6
    assert listed[0]["reports_count"] == 2
    assert listed[1]["source_ip"] == "198.51.100.2"
    assert listed[1]["message_count"] == 1

    assert detail is not None
    assert detail["source_ip"] == "198.51.100.1"
    assert detail["message_count"] == 6
    assert detail["records_count"] == 2
    assert detail["unique_domains"] == ["alpha.test", "beta.test"]
    assert detail["dkim_failures"] == 1
    assert detail["spf_failures"] == 1

    assert history == [
        {"bucket": "alpha.test", "message_count": 4},
        {"bucket": "beta.test", "message_count": 2},
    ]
    assert len(records) == 2


async def test_source_intelligence_returns_none_for_unknown_source() -> None:
    service = SourceIntelligenceService(record_repository=FakeRecordRepository())

    detail = await service.get_source_detail(tenant_id="tenant-s", source_ip="192.0.2.99")
    history = await service.source_history(tenant_id="tenant-s", source_ip="192.0.2.99")

    assert detail is None
    assert history == []


def test_source_intelligence_helpers_handle_edge_values() -> None:
    assert _record({"record": {"source_ip": "x"}}) == {"source_ip": "x"}
    assert _record({"record": 123}) == {}

    assert _as_int(True, default=7) == 1
    assert _as_int(9, default=7) == 9
    assert _as_int(3.8, default=7) == 3
    assert _as_int(" 5 ", default=7) == 5
    assert _as_int("", default=7) == 7
    assert _as_int("bad", default=7) == 7
