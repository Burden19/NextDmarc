from fastapi import APIRouter, Depends, status

from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.repositories.incident_repository import IncidentEntity, IncidentRepository
from app.schemas.incidents import IncidentResponse

router = APIRouter(prefix="/incidents", tags=["incidents"])
tenant_context_dep = Depends(get_tenant_context)


def _to_response(item: IncidentEntity) -> IncidentResponse:
    return IncidentResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        severity=item.severity,
        status=item.status,
        message=item.message,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    tenant: TenantContext = tenant_context_dep,
) -> list[IncidentResponse]:
    repository = IncidentRepository()
    return [
        _to_response(item)
        for item in await repository.list(tenant_id=str(tenant.tenant_id), limit=100)
    ]


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    tenant: TenantContext = tenant_context_dep,
) -> IncidentResponse:
    repository = IncidentRepository()
    found = await repository.get_by_id(tenant_id=str(tenant.tenant_id), incident_id=incident_id)
    if found is None:
        raise AppError(message="Incident not found", status_code=404, code="incident_not_found")
    return _to_response(found)


@router.post(
    "/{incident_id}/close",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
)
async def close_incident(
    incident_id: str,
    tenant: TenantContext = tenant_context_dep,
) -> IncidentResponse:
    repository = IncidentRepository()
    closed = await repository.close(tenant_id=str(tenant.tenant_id), incident_id=incident_id)
    if closed is None:
        raise AppError(message="Incident not found", status_code=404, code="incident_not_found")
    return _to_response(closed)
