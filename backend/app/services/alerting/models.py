from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AlertSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(StrEnum):
    EMAIL = "email"
    SLACK = "slack"
    SIEM = "siem"


@dataclass(slots=True)
class AlertNotification:
    tenant_id: str
    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    source: str | None = None
    occurred_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DispatchResult:
    channel: AlertChannel
    delivered: bool
    detail: str
