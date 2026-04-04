from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.schemas.mailboxes import (
    MailboxCreateRequest,
    MailboxResponse,
    MailboxTestResponse,
    MailboxUpdateRequest,
    ManualTriggerResponse,
)
from app.services.mailbox_store import MailboxRecord, get_mailbox_store
from app.workers.tasks.collect import collect_mailbox_reports

router = APIRouter(prefix="/mailboxes", tags=["mailboxes"])
tenant_context_dep = Depends(get_tenant_context)


def _to_response(item: MailboxRecord) -> MailboxResponse:
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


@router.post("", response_model=MailboxResponse, status_code=status.HTTP_201_CREATED)
async def create_mailbox(
    payload: MailboxCreateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> MailboxResponse:
    store = get_mailbox_store()
    created = store.create(
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
    store = get_mailbox_store()
    return [_to_response(item) for item in store.list(tenant_id=tenant.tenant_id)]


@router.get("/{mailbox_id}", response_model=MailboxResponse)
async def get_mailbox(
    mailbox_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> MailboxResponse:
    store = get_mailbox_store()
    found = store.get(tenant_id=tenant.tenant_id, mailbox_id=mailbox_id)
    if found is None:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")
    return _to_response(found)


@router.patch("/{mailbox_id}", response_model=MailboxResponse)
async def update_mailbox(
    mailbox_id: UUID,
    payload: MailboxUpdateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> MailboxResponse:
    store = get_mailbox_store()
    updated = store.update(
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
    store = get_mailbox_store()
    deleted = store.delete(tenant_id=tenant.tenant_id, mailbox_id=mailbox_id)
    if not deleted:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")


@router.post("/{mailbox_id}/test", response_model=MailboxTestResponse)
async def test_mailbox_connection(
    mailbox_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> MailboxTestResponse:
    store = get_mailbox_store()
    found = store.get(tenant_id=tenant.tenant_id, mailbox_id=mailbox_id)
    if found is None:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")
    return MailboxTestResponse(mailbox_id=found.id, status="ok")


@router.post("/{mailbox_id}/trigger-collect", response_model=ManualTriggerResponse)
async def manual_trigger_collect(
    mailbox_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> ManualTriggerResponse:
    store = get_mailbox_store()
    found = store.get(tenant_id=tenant.tenant_id, mailbox_id=mailbox_id)
    if found is None:
        raise AppError(message="Mailbox not found", status_code=404, code="mailbox_not_found")

    collect_mailbox_reports.delay(
        tenant_id=str(found.tenant_id),
        mailbox_id=str(found.id),
        username=found.username,
        password=found.password,
        mailbox=found.mailbox,
    )
    return ManualTriggerResponse(mailbox_id=found.id, status="queued")
