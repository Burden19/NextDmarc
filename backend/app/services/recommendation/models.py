from dataclasses import dataclass


@dataclass(slots=True)
class RecommendationItem:
    code: str
    title: str
    detail: str
    severity: str


@dataclass(slots=True)
class RecommendationResult:
    tenant_id: str
    report_db_id: str
    maturity_score: int
    maturity_level: str
    items: list[RecommendationItem]
