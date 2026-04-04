from datetime import datetime

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: str
    tenant_id: str
    domain_id: str
    report_id: str
    reporter_org: str
    date_range_begin: datetime
    date_range_end: datetime
    created_at: datetime


class PaginatedReportsResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_previous: bool
