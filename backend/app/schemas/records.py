from pydantic import BaseModel


class PaginatedRecordsResponse(BaseModel):
    items: list[dict[str, object]]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_previous: bool


class CsvExportResponse(BaseModel):
    content: str
