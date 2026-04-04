import gzip
from io import BytesIO
from zipfile import ZipFile

import pytest
from app.services.collector.attachment_decompressor import (
    AttachmentDecompressionError,
    AttachmentDecompressor,
)


def test_decompressor_returns_plain_attachment_when_not_compressed() -> None:
    decompressor = AttachmentDecompressor()

    files = decompressor.decompress(filename="report.xml", payload=b"<xml/>")

    assert len(files) == 1
    assert files[0].filename == "report.xml"
    assert files[0].content == b"<xml/>"


def test_decompressor_extracts_gzip_payload() -> None:
    decompressor = AttachmentDecompressor()
    payload = gzip.compress(b"<feedback/>")

    files = decompressor.decompress(filename="aggregate.xml.gz", payload=payload)

    assert len(files) == 1
    assert files[0].filename == "aggregate.xml"
    assert files[0].content == b"<feedback/>"


def test_decompressor_extracts_zip_payload() -> None:
    decompressor = AttachmentDecompressor()
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("one.xml", b"<one/>")
        archive.writestr("two.xml", b"<two/>")

    files = decompressor.decompress(filename="reports.zip", payload=stream.getvalue())

    assert [item.filename for item in files] == ["one.xml", "two.xml"]
    assert [item.content for item in files] == [b"<one/>", b"<two/>"]


def test_decompressor_blocks_unsafe_zip_paths() -> None:
    decompressor = AttachmentDecompressor()
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("../escape.xml", b"<x/>")

    with pytest.raises(AttachmentDecompressionError):
        decompressor.decompress(filename="unsafe.zip", payload=stream.getvalue())
