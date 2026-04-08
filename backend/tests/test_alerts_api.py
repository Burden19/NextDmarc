from dataclasses import replace
from datetime import UTC, datetime

from app.api.v1 import alerts as alerts_module
from app.main import app
from app.repositories.alert_repository import AlertAuditEntity, AlertEntity, AlertTriageResult
from app.repositories.pagination import Page
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class FakeAlertRepository:
    def __init__(self) -> None:
        now = datetime(2026, 4, 6, tzinfo=UTC)
        self.alert = AlertEntity(
            id="alert-1",
            tenant_id=TEST_TENANT_ID,
            domain_id=None,
            severity="high",
            status="new",
            message="Suspicious source",
            assignee=None,
            escalation_level=0,
            created_at=now,
            updated_at=now,
        )
        self.secondary_alert = AlertEntity(
            id="alert-2",
            tenant_id=TEST_TENANT_ID,
            domain_id=None,
            severity="low",
            status="investigating",
            message="Mailbox spike",
            assignee="analyst-2",
            escalation_level=0,
            created_at=datetime(2026, 4, 5, tzinfo=UTC),
            updated_at=datetime(2026, 4, 5, tzinfo=UTC),
        )
        self._audits: list[AlertAuditEntity] = []

    async def list_paginated(
        self,
        *,
        tenant_id: str,
        page: int,
        page_size: int,
        status: str | None = None,
        severity: str | None = None,
    ) -> Page[AlertEntity]:
        items = [self.alert, self.secondary_alert]
        filtered = [item for item in items if item.tenant_id == tenant_id]

        normalized_status = (status or "").strip().lower()
        if normalized_status:
            filtered = [item for item in filtered if item.status.lower() == normalized_status]

        normalized_severity = (severity or "").strip().lower()
        if normalized_severity:
            filtered = [item for item in filtered if item.severity.lower() == normalized_severity]

        filtered.sort(key=lambda item: item.created_at, reverse=True)
        start = (page - 1) * page_size
        sliced = filtered[start : start + page_size]
        return Page(items=sliced, total=len(filtered), page=page, page_size=page_size)

    async def get_by_id(self, *, tenant_id: str, alert_id: str) -> AlertEntity | None:
        if tenant_id != self.alert.tenant_id or alert_id != self.alert.id:
            return None
        return self.alert

    async def list_audit(self, *, tenant_id: str, alert_id: str) -> list[AlertAuditEntity]:
        if tenant_id != self.alert.tenant_id or alert_id != self.alert.id:
            return []
        return list(self._audits)

    async def update_status(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        status: str,
        actor: str | None = None,
        comment: str | None = None,
    ) -> AlertTriageResult | None:
        if not self._matches(tenant_id=tenant_id, alert_id=alert_id):
            return None
        self.alert = replace(self.alert, status=status, updated_at=datetime.now(tz=UTC))
        audit = self._append_audit(
            action="status_update",
            actor=actor,
            comment=comment,
            details={"status": status},
        )
        return AlertTriageResult(alert=self.alert, audit=audit)

    async def assign(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        assignee: str,
        actor: str | None = None,
        comment: str | None = None,
    ) -> AlertTriageResult | None:
        if not self._matches(tenant_id=tenant_id, alert_id=alert_id):
            return None
        self.alert = replace(self.alert, assignee=assignee, updated_at=datetime.now(tz=UTC))
        audit = self._append_audit(
            action="assign",
            actor=actor,
            comment=comment,
            details={"assignee": assignee},
        )
        return AlertTriageResult(alert=self.alert, audit=audit)

    async def add_comment(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        comment: str,
        actor: str | None = None,
    ) -> AlertTriageResult | None:
        if not self._matches(tenant_id=tenant_id, alert_id=alert_id):
            return None
        self.alert = replace(self.alert, updated_at=datetime.now(tz=UTC))
        audit = self._append_audit(
            action="comment",
            actor=actor,
            comment=comment,
            details={},
        )
        return AlertTriageResult(alert=self.alert, audit=audit)

    async def escalate(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        actor: str | None = None,
        comment: str | None = None,
        target_severity: str | None = None,
    ) -> AlertTriageResult | None:
        if not self._matches(tenant_id=tenant_id, alert_id=alert_id):
            return None
        next_severity = target_severity or _next_severity(self.alert.severity)
        next_level = self.alert.escalation_level + 1
        self.alert = replace(
            self.alert,
            severity=next_severity,
            escalation_level=next_level,
            updated_at=datetime.now(tz=UTC),
        )
        audit = self._append_audit(
            action="escalate",
            actor=actor,
            comment=comment,
            details={
                "to_severity": next_severity,
                "escalation_level": next_level,
            },
        )
        return AlertTriageResult(alert=self.alert, audit=audit)

    def _append_audit(
        self,
        *,
        action: str,
        actor: str | None,
        comment: str | None,
        details: dict[str, object],
    ) -> AlertAuditEntity:
        audit = AlertAuditEntity(
            id=f"audit-{len(self._audits) + 1}",
            tenant_id=self.alert.tenant_id,
            alert_id=self.alert.id,
            action=action,
            actor=actor,
            comment=comment,
            details=details,
            created_at=datetime.now(tz=UTC),
        )
        self._audits.append(audit)
        return audit

    def _matches(self, *, tenant_id: str, alert_id: str) -> bool:
        return tenant_id == self.alert.tenant_id and alert_id == self.alert.id


class FakeRealtimePublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def publish_event(
        self,
        *,
        tenant_id: str,
        event_type: str,
        alert_id: str,
        payload: dict[str, object],
    ) -> None:
        self.events.append(
            {
                "tenant_id": tenant_id,
                "event_type": event_type,
                "alert_id": alert_id,
                "payload": payload,
            }
        )


def _next_severity(current: str) -> str:
    if current == "low":
        return "medium"
    if current == "medium":
        return "high"
    return "critical"


def test_alerts_triage_actions_and_audit_trail(monkeypatch: MonkeyPatch) -> None:
    fake_repository = FakeAlertRepository()
    realtime_publisher = FakeRealtimePublisher()
    monkeypatch.setattr(alerts_module, "AlertRepository", lambda: fake_repository)
    monkeypatch.setattr(alerts_module, "_build_realtime_publisher", lambda: realtime_publisher)

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    status_response = client.post(
        "/api/v1/alerts/alert-1/status",
        headers=headers,
        json={"status": "investigating", "actor": "soc@example.test"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["alert"]["status"] == "investigating"
    assert status_response.json()["audit"]["action"] == "status_update"

    assign_response = client.post(
        "/api/v1/alerts/alert-1/assign",
        headers=headers,
        json={"assignee": "analyst-1", "actor": "lead@example.test"},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["alert"]["assignee"] == "analyst-1"

    comment_response = client.post(
        "/api/v1/alerts/alert-1/comment",
        headers=headers,
        json={"comment": "Investigating failure source", "actor": "analyst-1"},
    )
    assert comment_response.status_code == 200
    assert comment_response.json()["audit"]["action"] == "comment"

    escalate_response = client.post(
        "/api/v1/alerts/alert-1/escalate",
        headers=headers,
        json={"comment": "Escalating for urgent response", "actor": "lead@example.test"},
    )
    assert escalate_response.status_code == 200
    assert escalate_response.json()["alert"]["severity"] == "critical"
    assert escalate_response.json()["alert"]["escalation_level"] == 1

    audit_response = client.get("/api/v1/alerts/alert-1/audit", headers=headers)
    assert audit_response.status_code == 200
    assert len(audit_response.json()) == 4
    assert audit_response.json()[-1]["action"] == "escalate"
    assert [item["event_type"] for item in realtime_publisher.events] == [
        "alert.status_updated",
        "alert.assigned",
        "alert.commented",
        "alert.escalated",
    ]


def test_alerts_list_supports_pagination_and_filters(monkeypatch: MonkeyPatch) -> None:
    fake_repository = FakeAlertRepository()
    monkeypatch.setattr(alerts_module, "AlertRepository", lambda: fake_repository)

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    listing = client.get("/api/v1/alerts?page=1&page_size=1", headers=headers)
    assert listing.status_code == 200
    listing_payload = listing.json()
    assert listing_payload["total"] == 2
    assert listing_payload["page"] == 1
    assert listing_payload["page_size"] == 1
    assert listing_payload["has_next"] is True
    assert len(listing_payload["items"]) == 1
    assert listing_payload["items"][0]["id"] == "alert-1"

    severity_filtered = client.get("/api/v1/alerts?severity=low", headers=headers)
    assert severity_filtered.status_code == 200
    severity_payload = severity_filtered.json()
    assert severity_payload["total"] == 1
    assert severity_payload["items"][0]["id"] == "alert-2"

    status_filtered = client.get("/api/v1/alerts?status=investigating", headers=headers)
    assert status_filtered.status_code == 200
    status_payload = status_filtered.json()
    assert status_payload["total"] == 1
    assert status_payload["items"][0]["id"] == "alert-2"


def test_alerts_triage_returns_not_found_for_unknown_alert(monkeypatch: MonkeyPatch) -> None:
    fake_repository = FakeAlertRepository()
    monkeypatch.setattr(alerts_module, "AlertRepository", lambda: fake_repository)

    client = TestClient(app)
    headers = {"X-Tenant-ID": TEST_TENANT_ID}

    response = client.post(
        "/api/v1/alerts/unknown-alert/status",
        headers=headers,
        json={"status": "closed"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "alert_not_found"
