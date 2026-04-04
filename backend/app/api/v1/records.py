from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.repositories.record_repository import RecordRepository
from app.schemas.records import PaginatedRecordsResponse

router = APIRouter(prefix="/records", tags=["records"])
tenant_context_dep = Depends(get_tenant_context)


@router.get("", response_model=PaginatedRecordsResponse)
async def search_records(
    query: str = Query(default="*"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    tenant: TenantContext = tenant_context_dep,
) -> PaginatedRecordsResponse:
    repository = RecordRepository()
    result = await repository.search(
        tenant_id=str(tenant.tenant_id),
        query=query,
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


@router.get("/{document_id}")
async def get_record(
    document_id: str,
    tenant: TenantContext = tenant_context_dep,
) -> dict[str, object]:
    repository = RecordRepository()
    found = await repository.get_by_id(document_id=document_id)
    if found is None or str(found.get("tenant_id", "")) != str(tenant.tenant_id):
        raise AppError(message="Record not found", status_code=404, code="record_not_found")
    return found


@router.get("/export/csv", response_class=PlainTextResponse)
async def export_records_csv(
    query: str = Query(default="*"),
    tenant: TenantContext = tenant_context_dep,
) -> str:
    repository = RecordRepository()
    return await repository.export_csv(tenant_id=str(tenant.tenant_id), query=query)
