import asyncio
import hashlib
from email import policy
from email.parser import BytesParser
from pathlib import PurePosixPath

from celery import Task
from redis import Redis

from app.core.config import get_settings
from app.repositories.mailbox_repository import MailboxEntity, get_mailbox_repository
from app.services.collector.attachment_decompressor import (
    AttachmentDecompressor,
    AttachmentPayload,
)
from app.services.collector.imap_client import ImapClient, resolve_imap_server
from app.services.collector.minio_uploader import MinioUploader
from app.workers.celery_app import celery_app

RUN_LOCK_TTL_SECONDS = 300
MESSAGE_IDEMPOTENCY_TTL_SECONDS = 7 * 24 * 3600


def _build_imap_client() -> ImapClient:
    return ImapClient()


def _build_decompressor() -> AttachmentDecompressor:
    return AttachmentDecompressor()


def _build_uploader() -> MinioUploader:
    return MinioUploader()


def _queue_parse_task(*, tenant_id: str, object_name: str) -> None:
    # Import lazily to avoid task-module import cycles at startup.
    from app.workers.tasks.parse import parse_report_object

    parse_report_object.delay(tenant_id=tenant_id, object_name=object_name)


def _build_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _retry_delay_seconds(retry_count: int) -> int:
    bounded_retry = retry_count if retry_count >= 0 else 0
    delay = 10 * (2**bounded_retry)
    return 300 if delay > 300 else delay


def _apply_mailbox_server_override(*, imap_client: object, server: str | None) -> None:
    if not server or not isinstance(imap_client, ImapClient):
        return

    settings = get_settings()
    host, port, use_ssl = resolve_imap_server(
        server=server,
        default_port=settings.imap_port,
        default_use_ssl=settings.imap_use_ssl,
    )
    imap_client.configure_connection(host=host, port=port, use_ssl=use_ssl)


@celery_app.task(name="app.workers.tasks.collect.poll_active_mailboxes")
def poll_active_mailboxes() -> dict[str, int]:
    enabled_mailboxes = asyncio.run(_list_enabled_mailboxes())

    queued = 0
    for mailbox in enabled_mailboxes:
        collect_mailbox_reports.delay(
            tenant_id=str(mailbox.tenant_id),
            mailbox_id=str(mailbox.id),
            username=mailbox.username,
            password=mailbox.password,
            server=mailbox.server,
            mailbox=mailbox.mailbox,
        )
        queued += 1

    return {"queued_mailboxes": queued}


async def _list_enabled_mailboxes() -> list[MailboxEntity]:
    mailbox_repository = get_mailbox_repository()
    return await mailbox_repository.list_enabled()


@celery_app.task(bind=True, name="app.workers.tasks.collect.collect_mailbox_reports", max_retries=5)
def collect_mailbox_reports(
    self: Task,
    *,
    tenant_id: str,
    mailbox_id: str,
    username: str,
    password: str,
    server: str | None = None,
    mailbox: str = "INBOX",
) -> dict[str, int]:
    try:
        return asyncio.run(
            _collect_mailbox_reports_async(
                tenant_id=tenant_id,
                mailbox_id=mailbox_id,
                username=username,
                password=password,
                server=server,
                mailbox=mailbox,
            )
        )
    except Exception as exc:
        countdown = _retry_delay_seconds(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


async def _collect_mailbox_reports_async(
    *,
    tenant_id: str,
    mailbox_id: str,
    username: str,
    password: str,
    server: str | None = None,
    mailbox: str,
) -> dict[str, int]:
    redis_client = _build_redis_client()
    run_key = f"collect:run:{tenant_id}:{mailbox_id}"

    run_acquired = await asyncio.to_thread(
        _set_key_if_absent,
        redis_client,
        run_key,
        RUN_LOCK_TTL_SECONDS,
    )
    if not run_acquired:
        return {
            "fetched_messages": 0,
            "processed_messages": 0,
            "skipped_messages": 0,
            "uploaded_objects": 0,
            "already_running": 1,
        }

    try:
        imap_client = _build_imap_client()
        _apply_mailbox_server_override(imap_client=imap_client, server=server)
        decompressor = _build_decompressor()
        uploader = _build_uploader()

        messages = await imap_client.fetch_unseen_messages(
            username=username,
            password=password,
            mailbox=mailbox,
        )

        processed_messages = 0
        skipped_messages = 0
        uploaded_objects = 0

        for message in messages:
            if not await asyncio.to_thread(
                _acquire_message_idempotency,
                redis_client,
                tenant_id,
                mailbox_id,
                message.uid,
                message.raw_message,
            ):
                skipped_messages += 1
                continue

            attachments = _extract_attachments(message.raw_message)
            if not attachments:
                object_name = _build_object_name(
                    tenant_id=tenant_id,
                    mailbox_id=mailbox_id,
                    message_uid=message.uid,
                    filename="message.eml",
                )
                await uploader.upload_bytes(
                    object_name=object_name,
                    payload=message.raw_message,
                    content_type="message/rfc822",
                )
                uploaded_objects += 1
                processed_messages += 1
                continue

            object_index = 0
            for attachment in attachments:
                decompressed = decompressor.decompress(
                    filename=attachment.filename,
                    payload=attachment.content,
                )
                for item in decompressed:
                    object_index += 1
                    object_name = _build_object_name(
                        tenant_id=tenant_id,
                        mailbox_id=mailbox_id,
                        message_uid=message.uid,
                        filename=f"{object_index:03d}_{_normalize_filename(item.filename)}",
                    )
                    await uploader.upload_bytes(
                        object_name=object_name,
                        payload=item.content,
                        content_type=_guess_content_type(item.filename),
                    )
                    if _is_xml_payload(item.filename) or _looks_like_xml_payload(item.content):
                        _queue_parse_task(tenant_id=tenant_id, object_name=object_name)
                    uploaded_objects += 1

            processed_messages += 1

        return {
            "fetched_messages": len(messages),
            "processed_messages": processed_messages,
            "skipped_messages": skipped_messages,
            "uploaded_objects": uploaded_objects,
            "already_running": 0,
        }
    finally:
        await asyncio.to_thread(redis_client.delete, run_key)


def _set_key_if_absent(redis_client: Redis, key: str, ttl_seconds: int) -> bool:
    result = redis_client.set(key, "1", nx=True, ex=ttl_seconds)
    return bool(result)


def _acquire_message_idempotency(
    redis_client: Redis,
    tenant_id: str,
    mailbox_id: str,
    uid: str,
    raw_message: bytes,
) -> bool:
    fingerprint = hashlib.sha256(raw_message).hexdigest()[:16]
    key = f"collect:message:{tenant_id}:{mailbox_id}:{uid}:{fingerprint}"
    return _set_key_if_absent(redis_client, key, MESSAGE_IDEMPOTENCY_TTL_SECONDS)


def _extract_attachments(raw_message: bytes) -> list[AttachmentPayload]:
    message = BytesParser(policy=policy.default).parsebytes(raw_message)
    attachments: list[AttachmentPayload] = []

    for part in message.iter_attachments():
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            continue

        content_type = (part.get_content_type() or "application/octet-stream").lower()
        filename = part.get_filename() or _default_attachment_filename(content_type=content_type)
        attachments.append(AttachmentPayload(filename=filename, content=payload))

    # Some providers place DMARC XML in an inline body part instead of using
    # Content-Disposition: attachment.
    if not attachments:
        for part in message.walk():
            if part.is_multipart():
                continue

            content_type = (part.get_content_type() or "").lower()
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes):
                continue

            if not _is_xml_content_type(content_type) and not _looks_like_xml_payload(payload):
                continue

            attachments.append(
                AttachmentPayload(
                    filename=_default_attachment_filename(content_type=content_type),
                    content=payload,
                )
            )

    return attachments


def _normalize_filename(filename: str) -> str:
    clean_name = PurePosixPath(filename).name
    return clean_name.replace(" ", "_")


def _build_object_name(
    *,
    tenant_id: str,
    mailbox_id: str,
    message_uid: str,
    filename: str,
) -> str:
    return f"tenants/{tenant_id}/mailboxes/{mailbox_id}/messages/{message_uid}/{filename}"


def _guess_content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".xml"):
        return "application/xml"
    if lower.endswith(".json"):
        return "application/json"
    if lower.endswith(".csv"):
        return "text/csv"
    return "application/octet-stream"


def _is_xml_payload(filename: str) -> bool:
    return filename.lower().endswith(".xml")


def _is_xml_content_type(content_type: str) -> bool:
    normalized = content_type.lower()
    return normalized in {"application/xml", "text/xml"} or normalized.endswith("+xml")


def _default_attachment_filename(*, content_type: str) -> str:
    normalized = content_type.lower()
    if _is_xml_content_type(normalized):
        return "attachment.xml"
    if normalized in {"application/gzip", "application/x-gzip"}:
        return "attachment.gz"
    if normalized in {"application/zip", "application/x-zip-compressed"}:
        return "attachment.zip"
    return "attachment.bin"


def _looks_like_xml_payload(payload: bytes) -> bool:
    head = payload.lstrip()[:512].lower()
    if not head:
        return False
    return head.startswith(b"<?xml") or head.startswith(b"<feedback")
