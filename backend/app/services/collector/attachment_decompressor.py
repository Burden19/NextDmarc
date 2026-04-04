import gzip
import io
from dataclasses import dataclass
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile


class AttachmentDecompressionError(Exception):
    pass


@dataclass(slots=True)
class AttachmentPayload:
    filename: str
    content: bytes


class AttachmentDecompressor:
    def __init__(self, *, max_entries: int = 100, max_total_size_bytes: int = 50_000_000) -> None:
        self.max_entries = max_entries
        self.max_total_size_bytes = max_total_size_bytes

    def decompress(self, *, filename: str, payload: bytes) -> list[AttachmentPayload]:
        lower_name = filename.lower()
        if lower_name.endswith(".gz"):
            return [self._decompress_gzip(filename=filename, payload=payload)]
        if lower_name.endswith(".zip"):
            return self._decompress_zip(payload=payload)
        return [AttachmentPayload(filename=filename, content=payload)]

    def _decompress_gzip(self, *, filename: str, payload: bytes) -> AttachmentPayload:
        try:
            content = gzip.decompress(payload)
        except OSError as exc:
            raise AttachmentDecompressionError("Invalid gzip attachment") from exc

        inner_name = filename[:-3] if filename.lower().endswith(".gz") else filename
        return AttachmentPayload(filename=inner_name or "attachment.xml", content=content)

    def _decompress_zip(self, *, payload: bytes) -> list[AttachmentPayload]:
        try:
            archive = ZipFile(io.BytesIO(payload))
        except BadZipFile as exc:
            raise AttachmentDecompressionError("Invalid zip attachment") from exc

        total_size = 0
        attachments: list[AttachmentPayload] = []
        with archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                if len(attachments) >= self.max_entries:
                    raise AttachmentDecompressionError("Too many files in zip attachment")

                path = PurePosixPath(info.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise AttachmentDecompressionError("Unsafe zip attachment path detected")

                content = archive.read(info)
                total_size += len(content)
                if total_size > self.max_total_size_bytes:
                    raise AttachmentDecompressionError("Zip attachment is too large")

                attachments.append(AttachmentPayload(filename=info.filename, content=content))

        if not attachments:
            raise AttachmentDecompressionError("Zip attachment did not contain files")
        return attachments
