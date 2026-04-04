from pydantic import BaseModel


class SourceSummaryResponse(BaseModel):
    source_ip: str
    message_count: int
    reports_count: int
    first_seen: str
    last_seen: str


class SourceDetailResponse(BaseModel):
    source_ip: str
    message_count: int
    records_count: int
    unique_domains: list[str]
    dkim_failures: int
    spf_failures: int


class SourceHistoryBucketResponse(BaseModel):
    bucket: str
    message_count: int


class SourceRecordsResponse(BaseModel):
    items: list[dict[str, object]]
