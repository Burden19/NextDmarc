from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.config import get_settings
from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.repositories.mailbox_repository import MailboxEntity, get_mailbox_repository
from app.schemas.mailboxes import (
    MailboxCreateRequest,
    MailboxResponse,
    MailboxTestResponse,
    MailboxUpdateRequest,
    ManualTriggerResponse,
)
from app.services.collector.imap_client import ImapClient, resolve_imap_server
from app.workers.tasks.collect import collect_mailbox_reports

router = APIRouter(prefix="/mailboxes", tags=["mailboxes"])
tenant_context_dep = Depends(get_tenant_context)


def _to_response(item: MailboxEntity) -> MailboxResponse:
    return MailboxResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        name=item.name,
        username=item.username,
        server=item.server,
        mailbox=item.mailbox,
        enabled=item.enabled,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _collect_workers_available() -> bool:
    try:
        active_workers = collect_mailbox_reports.app.control.ping(timeout=0.5)
    except Exception:
        return False
    return bool(active_workers)


async def _test_mailbox_imap_connection(
    *,
    server: str,
    username: str,
    password: str,
    mailbox: str,
) -> None:
    settings = get_settings()
    host, port, use_ssl = resolve_imap_server(
        server=server,
        default_port=settings.imap_port,
        default_use_ssl=settings.imap_use_ssl,
    )
    imap_client = ImapClient()
    imap_client.configure_connection(host=host, port=port, use_ssl=use_ssl)
    await imap_client.test_connection(
        username=username,
        password=password,
        mailbox=mailbox,
    )


@router.post("", response_model=MailboxResponse, status_code=status.HTTP_201_CREATED)
async def create_mailbox(
    payload: MailboxCreateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> MailboxResponse:
    repository = get_mailbox_repository()
    created = await repository.create(
        tenant_id=tenant.tenant_id,
        name=payload.name,
        username=payload.username,
        password=payload.password,
        server=payload.server,
        mailbox=payload.mailbox,
    )
    return _to_response(created)


@router.get("", response_model=list[MailboxResponse])
async def list_mailboxes(
    tenant: TenantContext = tenant_context_dep,
) -> list[MailboxResponse]:
    repository = get_mailbox_repository()
    return [_to_response(item) for item in await repository.list(tenant_id=tenant.tenant_id)]


@router.get("/{mailbox_id}", response_model=MailboxResponse)
async def get_mailbox(
    mailbox_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> MailboxResponse:
    repository = get_mailbox_repository()
    found = await repository.get(tenant_id=tenant.tenant_id, mailbox_id=mailbox_id)
    if found is None:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")
    return _to_response(found)


@router.patch("/{mailbox_id}", response_model=MailboxResponse)
async def update_mailbox(
    mailbox_id: UUID,
    payload: MailboxUpdateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> MailboxResponse:
    repository = get_mailbox_repository()
    updated = await repository.update(
        tenant_id=tenant.tenant_id,
        mailbox_id=mailbox_id,
        name=payload.name,
        username=payload.username,
        password=payload.password,
        server=payload.server,
        mailbox=payload.mailbox,
        enabled=payload.enabled,
    )
    if updated is None:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")
    return _to_response(updated)


@router.delete("/{mailbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mailbox(
    mailbox_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> None:
    repository = get_mailbox_repository()
    deleted = await repository.delete(tenant_id=tenant.tenant_id, mailbox_id=mailbox_id)
    if not deleted:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")


@router.post("/{mailbox_id}/test", response_model=MailboxTestResponse)
async def test_mailbox_connection(
    mailbox_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> MailboxTestResponse:
    repository = get_mailbox_repository()
    found = await repository.get(tenant_id=tenant.tenant_id, mailbox_id=mailbox_id)
    if found is None:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")

    try:
        await _test_mailbox_imap_connection(
            server=found.server,
            username=found.username,
            password=found.password,
            mailbox=found.mailbox,
        )
    except ValueError as exc:
        raise AppError(message=str(exc), status_code=400, code="mailbox_test_failed") from exc
    except Exception as exc:
        raise AppError(
            message=f"IMAP connection test failed: {exc}",
            status_code=400,
            code="mailbox_test_failed",
        ) from exc

    return MailboxTestResponse(mailbox_id=found.id, status="ok")


@router.post("/{mailbox_id}/trigger-collect", response_model=ManualTriggerResponse)
async def manual_trigger_collect(
    mailbox_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> ManualTriggerResponse:
    repository = get_mailbox_repository()
    found = await repository.get(tenant_id=tenant.tenant_id, mailbox_id=mailbox_id)
    if found is None:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")

    if not _collect_workers_available():
        raise AppError(
            message="Collection worker is not running. Start Celery worker and retry.",
            status_code=503,
            code="collector_worker_unavailable",
        )

    collect_mailbox_reports.delay(
        tenant_id=str(found.tenant_id),
        mailbox_id=str(found.id),
        username=found.username,
        password=found.password,
        server=found.server,
        mailbox=found.mailbox,
    )
    return ManualTriggerResponse(mailbox_id=found.id, status="queued")
