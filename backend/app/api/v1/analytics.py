from fastapi import APIRouter, Depends, Query

from app.core.dependencies import TenantContext, get_tenant_context
from app.schemas.analytics import (
    ConformanceResponse,
    RiskTrendResponse,
    SpfDkimBreakdownResponse,
    TopSourcesResponse,
    VolumeResponse,
)
from app.services.analytics.metrics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
tenant_context_dep = Depends(get_tenant_context)


@router.get("/conformance", response_model=ConformanceResponse)
async def get_conformance(
    tenant: TenantContext = tenant_context_dep,
) -> ConformanceResponse:
    service = AnalyticsService()
    return ConformanceResponse.model_validate(
        await service.conformance(tenant_id=str(tenant.tenant_id))
    )


@router.get("/risk-trend", response_model=RiskTrendResponse)
async def get_risk_trend(
    tenant: TenantContext = tenant_context_dep,
) -> RiskTrendResponse:
    service = AnalyticsService()
    return RiskTrendResponse.model_validate(service.risk_trend(tenant_id=str(tenant.tenant_id)))


@router.get("/top-sources", response_model=TopSourcesResponse)
async def get_top_sources(
    limit: int = Query(default=10, ge=1, le=100),
    tenant: TenantContext = tenant_context_dep,
) -> TopSourcesResponse:
    service = AnalyticsService()
    return TopSourcesResponse.model_validate(
        await service.top_sources(tenant_id=str(tenant.tenant_id), limit=limit)
    )


@router.get("/volume", response_model=VolumeResponse)
async def get_volume(tenant: TenantContext = tenant_context_dep) -> VolumeResponse:
    service = AnalyticsService()
    return VolumeResponse.model_validate(await service.volume(tenant_id=str(tenant.tenant_id)))


@router.get("/spf-dkim-breakdown", response_model=SpfDkimBreakdownResponse)
async def get_spf_dkim_breakdown(
    tenant: TenantContext = tenant_context_dep,
) -> SpfDkimBreakdownResponse:
    service = AnalyticsService()
    return SpfDkimBreakdownResponse.model_validate(
        await service.spf_dkim_breakdown(tenant_id=str(tenant.tenant_id))
    )
