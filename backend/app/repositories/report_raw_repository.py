import asyncio
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Protocol

from minio import Minio

from app.core.config import Settings, get_settings
from app.repositories.pagination import Page, build_offset_limit


class MinioObjectResponse(Protocol):
    def read(self) -> bytes: ...

    def close(self) -> None: ...

    def release_conn(self) -> None: ...


class MinioListItem(Protocol):
    object_name: str
    size: int
    etag: str
    last_modified: datetime | None


class MinioClientLike(Protocol):
    def bucket_exists(self, bucket_name: str) -> bool: ...

    def make_bucket(self, bucket_name: str) -> None: ...

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BytesIO,
        length: int,
        content_type: str,
    ) -> object: ...

    def get_object(self, bucket_name: str, object_name: str) -> MinioObjectResponse: ...

    def remove_object(self, bucket_name: str, object_name: str) -> None: ...

    def list_objects(
        self,
        bucket_name: str,
        prefix: str,
        recursive: bool,
    ) -> Iterable[MinioListItem]: ...


@dataclass(slots=True)
class RawReportObject:
    object_name: str
    size: int
    etag: str
    last_modified: datetime | None


class ReportRawRepository:
    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[[], MinioClientLike] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._bucket = self._settings.minio_bucket_reports

        if client_factory is not None:
            self._client = client_factory()
        else:
            self._client = Minio(
                endpoint=self._settings.minio_endpoint,
                access_key=self._settings.minio_access_key,
                secret_key=self._settings.minio_secret_key,
                secure=self._settings.minio_secure,
            )

    async def create(
        self,
        *,
        object_name: str,
        payload: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        await self._ensure_bucket_exists()
        stream = BytesIO(payload)
        await asyncio.to_thread(
            self._client.put_object,
            self._bucket,
            object_name,
            stream,
            len(payload),
            content_type,
        )
        return object_name

    async def get(self, *, object_name: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, self._bucket, object_name)
        try:
            return await asyncio.to_thread(response.read)
        finally:
            await asyncio.to_thread(response.close)
            await asyncio.to_thread(response.release_conn)

    async def delete(self, *, object_name: str) -> None:
        await asyncio.to_thread(self._client.remove_object, self._bucket, object_name)

    async def list(
        self,
        *,
        prefix: str,
        page: int,
        page_size: int,
    ) -> Page[RawReportObject]:
        offset, limit = build_offset_limit(page=page, page_size=page_size)

        listed = await asyncio.to_thread(
            lambda: list(self._client.list_objects(self._bucket, prefix=prefix, recursive=True))
        )
        listed.sort(key=lambda item: item.object_name)

        total = len(listed)
        selected = listed[offset : offset + limit]

        return Page(
            items=[
                RawReportObject(
                    object_name=item.object_name,
                    size=item.size,
                    etag=item.etag,
                    last_modified=item.last_modified,
                )
                for item in selected
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def _ensure_bucket_exists(self) -> None:
        exists = await asyncio.to_thread(self._client.bucket_exists, self._bucket)
        if exists:
            return
        await asyncio.to_thread(self._client.make_bucket, self._bucket)
