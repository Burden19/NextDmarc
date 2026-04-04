from fastapi import APIRouter, Depends, Query

from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.repositories.record_repository import RecordRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.records import PaginatedRecordsResponse
from app.schemas.reports import PaginatedReportsResponse, ReportResponse

router = APIRouter(prefix="/reports", tags=["reports"])
tenant_context_dep = Depends(get_tenant_context)


def _to_report_response(item) -> ReportResponse:
    return ReportResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        domain_id=item.domain_id,
        report_id=item.report_id,
        reporter_org=item.reporter_org,
        date_range_begin=item.date_range_begin,
        date_range_end=item.date_range_end,
        created_at=item.created_at,
    )


@router.get("", response_model=PaginatedReportsResponse)
async def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    tenant: TenantContext = tenant_context_dep,
) -> PaginatedReportsResponse:
    repository = ReportRepository()
    result = await repository.list(tenant_id=str(tenant.tenant_id), page=page, page_size=page_size)

    return PaginatedReportsResponse(
        items=[_to_report_response(item) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=result.pages,
        has_next=result.has_next,
        has_previous=result.has_previous,
    )


@router.get("/{report_db_id}", response_model=ReportResponse)
async def get_report(
    report_db_id: str,
    tenant: TenantContext = tenant_context_dep,
) -> ReportResponse:
    repository = ReportRepository()
    found = await repository.get_by_id(tenant_id=str(tenant.tenant_id), report_db_id=report_db_id)
    if found is None:
        raise AppError(message="Report not found", status_code=404, code="report_not_found")
    return _to_report_response(found)


@router.get("/{report_db_id}/records", response_model=PaginatedRecordsResponse)
async def list_report_records(
    report_db_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    tenant: TenantContext = tenant_context_dep,
) -> PaginatedRecordsResponse:
    repository = RecordRepository()
    result = await repository.search(
        tenant_id=str(tenant.tenant_id),
        query=f'report_db_id:"{report_db_id}"',
        page=page,
        page_size=page_size,
    )
    return PaginatedRecordsResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=result.pages,
        has_next=result.has_next,
        has_previous=result.has_previous,
    )
