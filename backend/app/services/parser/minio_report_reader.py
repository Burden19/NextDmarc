import asyncio
from collections.abc import Callable
from typing import Protocol

from minio import Minio

from app.core.config import Settings, get_settings


class MinioObjectResponse(Protocol):
    def read(self) -> bytes: ...

    def close(self) -> None: ...

    def release_conn(self) -> None: ...


class MinioClientLike(Protocol):
    def get_object(self, bucket_name: str, object_name: str) -> MinioObjectResponse: ...


class MinioReportReader:
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

    async def read_bytes(self, *, object_name: str) -> bytes:
        response = await asyncio.to_thread(
            self._client.get_object,
            self._bucket,
            object_name,
        )
        try:
            return await asyncio.to_thread(response.read)
        finally:
            await asyncio.to_thread(response.close)
            await asyncio.to_thread(response.release_conn)
