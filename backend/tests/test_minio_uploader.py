from dataclasses import dataclass
from io import BytesIO

import pytest
from app.services.collector.minio_uploader import MinioUploader


@dataclass
class UploadedObject:
    bucket_name: str
    object_name: str
    content: bytes
    content_type: str


class FakeMinioClient:
    def __init__(self) -> None:
        self.created_buckets: list[str] = []
        self.existing_buckets: set[str] = set()
        self.uploads: list[UploadedObject] = []

    def bucket_exists(self, bucket_name: str) -> bool:
        return bucket_name in self.existing_buckets

    def make_bucket(self, bucket_name: str) -> None:
        self.created_buckets.append(bucket_name)
        self.existing_buckets.add(bucket_name)

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BytesIO,
        length: int,
        content_type: str,
    ) -> object:
        content = data.read(length)
        self.uploads.append(
            UploadedObject(
                bucket_name=bucket_name,
                object_name=object_name,
                content=content,
                content_type=content_type,
            )
        )
        return object()


@pytest.mark.asyncio
async def test_minio_uploader_creates_bucket_and_uploads_bytes() -> None:
    fake_client = FakeMinioClient()
    uploader = MinioUploader(
        client_factory=lambda: fake_client,
    )

    location = await uploader.upload_bytes(
        object_name="tenant-1/report.xml",
        payload=b"<feedback/>",
        content_type="application/xml",
    )

    assert fake_client.created_buckets == ["dmarc-raw-reports"]
    assert len(fake_client.uploads) == 1
    upload = fake_client.uploads[0]
    assert upload.bucket_name == "dmarc-raw-reports"
    assert upload.object_name == "tenant-1/report.xml"
    assert upload.content == b"<feedback/>"
    assert upload.content_type == "application/xml"
    assert location == "s3://dmarc-raw-reports/tenant-1/report.xml"
