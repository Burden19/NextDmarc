from pydantic import BaseModel


class ConformanceResponse(BaseModel):
    total_messages: int
    conformance_rate: float
    dkim_pass_rate: float
    spf_pass_rate: float
    dmarc_pass_rate: float


class RiskTrendPoint(BaseModel):
    at: str
    score: int
    risk_state: str


class RiskTrendResponse(BaseModel):
    points: list[RiskTrendPoint]


class TopSourceItem(BaseModel):
    source_ip: str
    message_count: int


class TopSourcesResponse(BaseModel):
    items: list[TopSourceItem]


class VolumeByDomainItem(BaseModel):
    domain: str
    message_count: int


class VolumeResponse(BaseModel):
    total_messages: int
    by_domain: list[VolumeByDomainItem]


class SpfDkimBreakdownResponse(BaseModel):
    spf_pass_dkim_pass: int
    spf_pass_dkim_fail: int
    spf_fail_dkim_pass: int
    spf_fail_dkim_fail: int
