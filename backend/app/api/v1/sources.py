from fastapi import APIRouter, Depends, Query

from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.schemas.sources import (
    SourceDetailResponse,
    SourceHistoryBucketResponse,
    SourceRecordsResponse,
    SourceSummaryResponse,
)
from app.services.sources.intelligence import SourceIntelligenceService

router = APIRouter(prefix="/sources", tags=["sources"])
tenant_context_dep = Depends(get_tenant_context)


@router.get("", response_model=list[SourceSummaryResponse])
async def list_sources(tenant: TenantContext = tenant_context_dep) -> list[SourceSummaryResponse]:
    service = SourceIntelligenceService()
    items = await service.list_sources(tenant_id=str(tenant.tenant_id))
    return [SourceSummaryResponse.model_validate(item) for item in items]


@router.get("/{source_ip}", response_model=SourceDetailResponse)
async def get_source_detail(
    source_ip: str,
    tenant: TenantContext = tenant_context_dep,
) -> SourceDetailResponse:
    service = SourceIntelligenceService()
    found = await service.get_source_detail(tenant_id=str(tenant.tenant_id), source_ip=source_ip)
    if found is None:
        raise AppError(message="Source not found", status_code=404, code="source_not_found")
    return SourceDetailResponse.model_validate(found)


@router.get("/{source_ip}/history", response_model=list[SourceHistoryBucketResponse])
async def get_source_history(
    source_ip: str,
    tenant: TenantContext = tenant_context_dep,
) -> list[SourceHistoryBucketResponse]:
    service = SourceIntelligenceService()
    items = await service.source_history(tenant_id=str(tenant.tenant_id), source_ip=source_ip)
    return [SourceHistoryBucketResponse.model_validate(item) for item in items]


@router.get("/{source_ip}/records", response_model=SourceRecordsResponse)
async def get_source_records(
    source_ip: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    tenant: TenantContext = tenant_context_dep,
) -> SourceRecordsResponse:
    service = SourceIntelligenceService()
    items = await service.records_for_source(
        tenant_id=str(tenant.tenant_id),
        source_ip=source_ip,
        page=page,
        page_size=page_size,
    )
    return SourceRecordsResponse(items=items)
