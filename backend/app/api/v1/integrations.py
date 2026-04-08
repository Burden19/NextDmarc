from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.schemas.integrations import (
    IntegrationCreateRequest,
    IntegrationResponse,
    IntegrationTestResponse,
    IntegrationUpdateRequest,
)
from app.services.integrations.store import IntegrationRecord, get_integration_store

router = APIRouter(prefix="/integrations", tags=["integrations"])
tenant_context_dep = Depends(get_tenant_context)


def _to_response(item: IntegrationRecord) -> IntegrationResponse:
    return IntegrationResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        name=item.name,
        kind=item.kind,
        config=item.config,
        enabled=item.enabled,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    payload: IntegrationCreateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> IntegrationResponse:
    store = get_integration_store()
    created = store.create(
        tenant_id=tenant.tenant_id,
        name=payload.name,
        kind=payload.kind,
        config=payload.config,
        enabled=payload.enabled,
    )
    return _to_response(created)


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    tenant: TenantContext = tenant_context_dep,
) -> list[IntegrationResponse]:
    store = get_integration_store()
    return [_to_response(item) for item in store.list(tenant_id=tenant.tenant_id)]


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> IntegrationResponse:
    store = get_integration_store()
    found = store.get(tenant_id=tenant.tenant_id, integration_id=integration_id)
    if found is None:
        raise AppError(
            message="Integration not found",
            status_code=404,
            code="integration_not_found",
        )
    return _to_response(found)


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    payload: IntegrationUpdateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> IntegrationResponse:
    store = get_integration_store()
    updated = store.update(
        tenant_id=tenant.tenant_id,
        integration_id=integration_id,
        name=payload.name,
        config=payload.config,
        enabled=payload.enabled,
    )
    if updated is None:
        raise AppError(
            message="Integration not found",
            status_code=404,
            code="integration_not_found",
        )
    return _to_response(updated)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> None:
    store = get_integration_store()
    deleted = store.delete(tenant_id=tenant.tenant_id, integration_id=integration_id)
    if not deleted:
        raise AppError(
            message="Integration not found",
            status_code=404,
            code="integration_not_found",
        )


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
async def test_integration_connector(
    integration_id: UUID,
    tenant: TenantContext = tenant_context_dep,
) -> IntegrationTestResponse:
    store = get_integration_store()
    tested = store.test_connector(
        tenant_id=tenant.tenant_id,
        integration_id=integration_id,
    )
    if tested is None:
        raise AppError(
            message="Integration not found",
            status_code=404,
            code="integration_not_found",
        )

    return IntegrationTestResponse(
        integration_id=tested.integration_id,
        status=tested.status,
        detail=tested.detail,
    )
