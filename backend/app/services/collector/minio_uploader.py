import asyncio
from collections.abc import Callable
from io import BytesIO
from typing import Protocol

from minio import Minio

from app.core.config import Settings, get_settings


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


class MinioUploader:
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

    async def ensure_bucket_exists(self) -> None:
        exists = await asyncio.to_thread(self._client.bucket_exists, self._bucket)
        if exists:
            return
        await asyncio.to_thread(self._client.make_bucket, self._bucket)

    async def upload_bytes(
        self,
        *,
        object_name: str,
        payload: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        await self.ensure_bucket_exists()
        stream = BytesIO(payload)
        await asyncio.to_thread(
            self._client.put_object,
            self._bucket,
            object_name,
            stream,
            len(payload),
            content_type,
        )
        return f"s3://{self._bucket}/{object_name}"
