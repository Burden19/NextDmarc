from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.schemas.recommendations import (
    RecommendationItemResponse,
    RecommendationResolveRequest,
    RecommendationResolveResponse,
    RecommendationResponse,
)
from app.services.recommendation.resolution_store import get_recommendation_resolution_store
from app.services.recommendation.store import (
    RecommendationEntry,
    RecommendationStore,
    get_recommendation_store,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
tenant_context_dep = Depends(get_tenant_context)


def _to_response(
    item: RecommendationEntry,
    *,
    resolved: bool,
    resolved_at: datetime | None,
) -> RecommendationResponse:
    return RecommendationResponse(
        tenant_id=item.tenant_id,
        report_db_id=item.report_db_id,
        maturity_score=item.maturity_score,
        maturity_level=item.maturity_level,
        items=[
            RecommendationItemResponse(
                code=recommendation.code,
                title=recommendation.title,
                detail=recommendation.detail,
                severity=recommendation.severity,
            )
            for recommendation in item.items
        ],
        created_at=item.created_at,
        resolved=resolved,
        resolved_at=resolved_at,
    )


@router.get("", response_model=list[RecommendationResponse])
async def list_recommendations(
    tenant: TenantContext = tenant_context_dep,
) -> list[RecommendationResponse]:
    store: RecommendationStore = get_recommendation_store()
    resolution_store = get_recommendation_resolution_store()

    tenant_id = str(tenant.tenant_id)
    history = list(reversed(store.history(tenant_id=tenant_id)))
    responses: list[RecommendationResponse] = []
    for item in history:
        resolution = resolution_store.get(tenant_id=tenant_id, report_db_id=item.report_db_id)
        responses.append(
            _to_response(
                item,
                resolved=False if resolution is None else resolution.resolved,
                resolved_at=None if resolution is None else resolution.resolved_at,
            )
        )
    return responses


@router.get("/{report_db_id}", response_model=RecommendationResponse)
async def get_recommendation_detail(
    report_db_id: str,
    tenant: TenantContext = tenant_context_dep,
) -> RecommendationResponse:
    store: RecommendationStore = get_recommendation_store()
    resolution_store = get_recommendation_resolution_store()

    tenant_id = str(tenant.tenant_id)
    found = next(
        (
            item
            for item in reversed(store.history(tenant_id=tenant_id))
            if item.report_db_id == report_db_id
        ),
        None,
    )
    if found is None:
        raise AppError(
            message="Recommendation not found",
            status_code=404,
            code="recommendation_not_found",
        )

    resolution = resolution_store.get(tenant_id=tenant_id, report_db_id=report_db_id)
    return _to_response(
        found,
        resolved=False if resolution is None else resolution.resolved,
        resolved_at=None if resolution is None else resolution.resolved_at,
    )


@router.post("/{report_db_id}/resolve", response_model=RecommendationResolveResponse)
async def resolve_recommendation(
    report_db_id: str,
    payload: RecommendationResolveRequest,
    tenant: TenantContext = tenant_context_dep,
) -> RecommendationResolveResponse:
    store: RecommendationStore = get_recommendation_store()
    resolution_store = get_recommendation_resolution_store()

    tenant_id = str(tenant.tenant_id)
    exists = any(item.report_db_id == report_db_id for item in store.history(tenant_id=tenant_id))
    if not exists:
        raise AppError(
            message="Recommendation not found",
            status_code=404,
            code="recommendation_not_found",
        )

    resolved = resolution_store.resolve(
        tenant_id=tenant_id,
        report_db_id=report_db_id,
        resolved=payload.resolved,
        comment=payload.comment,
    )
    return RecommendationResolveResponse(
        tenant_id=resolved.tenant_id,
        report_db_id=resolved.report_db_id,
        resolved=resolved.resolved,
        resolved_at=resolved.resolved_at,
        comment=resolved.comment,
    )
