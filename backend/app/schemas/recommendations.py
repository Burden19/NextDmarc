from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationItemResponse(BaseModel):
    code: str
    title: str
    detail: str
    severity: str


class RecommendationResponse(BaseModel):
    tenant_id: str
    report_db_id: str
    maturity_score: int
    maturity_level: str
    items: list[RecommendationItemResponse]
    created_at: datetime
    resolved: bool
    resolved_at: datetime | None


class RecommendationResolveRequest(BaseModel):
    resolved: bool = True
    comment: str | None = Field(default=None, max_length=4000)


class RecommendationResolveResponse(BaseModel):
    tenant_id: str
    report_db_id: str
    resolved: bool
    resolved_at: datetime | None
    comment: str | None
