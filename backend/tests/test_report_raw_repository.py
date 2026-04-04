from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO

import pytest
from app.repositories.report_raw_repository import ReportRawRepository


@dataclass
class FakeListItem:
    object_name: str
    size: int
    etag: str
    last_modified: datetime | None


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        return None

    def release_conn(self) -> None:
        return None


class FakeMinioClient:
    def __init__(self) -> None:
        self.bucket_created = False
        self.storage: dict[str, bytes] = {}

    def bucket_exists(self, bucket_name: str) -> bool:
        _ = bucket_name
        return self.bucket_created

    def make_bucket(self, bucket_name: str) -> None:
        _ = bucket_name
        self.bucket_created = True

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BytesIO,
        length: int,
        content_type: str,
    ) -> object:
        _ = bucket_name
        _ = content_type
        self.storage[object_name] = data.read(length)
        return object()

    def get_object(self, bucket_name: str, object_name: str) -> FakeResponse:
        _ = bucket_name
        return FakeResponse(self.storage[object_name])

    def remove_object(self, bucket_name: str, object_name: str) -> None:
        _ = bucket_name
        del self.storage[object_name]

    def list_objects(self, bucket_name: str, prefix: str, recursive: bool):
        _ = bucket_name
        _ = recursive
        for name in sorted(self.storage.keys()):
            if name.startswith(prefix):
                yield FakeListItem(
                    object_name=name,
                    size=len(self.storage[name]),
                    etag="etag-1",
                    last_modified=datetime(2026, 4, 4, tzinfo=UTC),
                )


@pytest.mark.asyncio
async def test_report_raw_repository_crud_and_pagination() -> None:
    client = FakeMinioClient()
    repo = ReportRawRepository(client_factory=lambda: client)

    await repo.create(object_name="reports/a.xml", payload=b"A", content_type="application/xml")
    await repo.create(object_name="reports/b.xml", payload=b"B", content_type="application/xml")

    loaded = await repo.get(object_name="reports/a.xml")
    page = await repo.list(prefix="reports/", page=1, page_size=1)
    await repo.delete(object_name="reports/a.xml")

    assert client.bucket_created is True
    assert loaded == b"A"
    assert page.total == 2
    assert len(page.items) == 1
    assert page.items[0].object_name == "reports/a.xml"
    assert "reports/a.xml" not in client.storage
