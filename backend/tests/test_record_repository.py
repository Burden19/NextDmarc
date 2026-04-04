import pytest
from app.repositories.record_repository import RecordRepository


class FakeIndices:
    async def exists(self, index: str) -> bool:
        _ = index
        return True

    async def create(self, index: str) -> None:
        _ = index


class FakeElasticsearch:
    def __init__(self) -> None:
        self.indices = FakeIndices()
        self.deleted: list[str] = []

    async def get(self, index: str, id: str):
        _ = index
        if id == "missing":
            from elasticsearch import NotFoundError

            raise NotFoundError(message="missing", meta=None, body={})
        return {"_source": {"report_id": "rid-1", "record": {"source_ip": "203.0.113.5"}}}

    async def search(self, index: str, body):
        _ = index
        _ = body
        return {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "report_id": "rid-1",
                            "record": {
                                "source_ip": "203.0.113.5",
                                "count": 2,
                                "dkim": "pass",
                                "spf": "fail",
                                "disposition": "none",
                            },
                        }
                    }
                ],
            }
        }

    async def delete(self, index: str, id: str):
        _ = index
        if id == "missing":
            from elasticsearch import NotFoundError

            raise NotFoundError(message="missing", meta=None, body={})
        self.deleted.append(id)


@pytest.mark.asyncio
async def test_record_repository_search_get_export_and_delete(monkeypatch) -> None:
    fake_es = FakeElasticsearch()
    monkeypatch.setattr(
        "app.repositories.record_repository.AsyncElasticsearch",
        lambda url: fake_es,
    )

    repo = RecordRepository()
    found = await repo.get_by_id(document_id="doc-1")
    page = await repo.search(tenant_id="tenant-1", query="*", page=1, page_size=20)
    csv_data = await repo.export_csv(tenant_id="tenant-1")
    deleted = await repo.delete(document_id="doc-1")
    missing = await repo.get_by_id(document_id="missing")

    assert found is not None
    assert found["report_id"] == "rid-1"
    assert page.total == 1
    assert len(page.items) == 1
    assert "report_id,source_ip,count,dkim,spf,disposition" in csv_data
    assert "rid-1,203.0.113.5,2,pass,fail,none" in csv_data
    assert deleted is True
    assert missing is None
