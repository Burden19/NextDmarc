from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.schemas.domains import (
    DomainCreateRequest,
    DomainPolicyResponse,
    DomainResponse,
    DomainUpdateRequest,
)
from app.services.domain_store import DomainRecord, get_domain_store

router = APIRouter(prefix="/domains", tags=["domains"])
tenant_context_dep = Depends(get_tenant_context)


def _to_response(item: DomainRecord) -> DomainResponse:
    return DomainResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        fqdn=item.fqdn,
        status=item.status,
        dmarc_policy=item.dmarc_policy,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def create_domain(
    payload: DomainCreateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> DomainResponse:
    store = get_domain_store()
    created = store.create(
        tenant_id=tenant.tenant_id,
        fqdn=payload.fqdn,
        dmarc_policy=payload.dmarc_policy,
    )
    return _to_response(created)


@router.get("", response_model=list[DomainResponse])
async def list_domains(tenant: TenantContext = tenant_context_dep) -> list[DomainResponse]:
    store = get_domain_store()
    return [_to_response(item) for item in store.list(tenant_id=tenant.tenant_id)]


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> DomainResponse:
    store = get_domain_store()
    found = store.get(tenant_id=tenant.tenant_id, domain_id=domain_id)
    if found is None:
        raise AppError(message="Domain not found", status_code=404, code="domain_not_found")
    return _to_response(found)


@router.patch("/{domain_id}", response_model=DomainResponse)
async def update_domain(
    domain_id: UUID,
    payload: DomainUpdateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> DomainResponse:
    store = get_domain_store()
    updated = store.update(
        tenant_id=tenant.tenant_id,
        domain_id=domain_id,
        fqdn=payload.fqdn,
        status=payload.status,
        dmarc_policy=payload.dmarc_policy,
    )
    if updated is None:
        raise AppError(message="Domain not found", status_code=404, code="domain_not_found")
    return _to_response(updated)


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> None:
    store = get_domain_store()
    deleted = store.delete(tenant_id=tenant.tenant_id, domain_id=domain_id)
    if not deleted:
        raise AppError(message="Domain not found", status_code=404, code="domain_not_found")


@router.get("/{domain_id}/policy", response_model=DomainPolicyResponse)
async def get_domain_policy(
    domain_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> DomainPolicyResponse:
    store = get_domain_store()
    found = store.get(tenant_id=tenant.tenant_id, domain_id=domain_id)
    if found is None:
        raise AppError(message="Domain not found", status_code=404, code="domain_not_found")
    return DomainPolicyResponse(
        domain_id=found.id,
        fqdn=found.fqdn,
        dmarc_policy=found.dmarc_policy,
    )
