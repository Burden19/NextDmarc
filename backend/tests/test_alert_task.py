import asyncio
from datetime import UTC, datetime

from app.repositories.alert_repository import AlertAuditEntity, AlertEntity
from app.services.alerting.models import (
    AlertChannel,
    AlertNotification,
    AlertSeverity,
    DispatchResult,
)
from app.workers.tasks import alert as alert_module
from pytest import MonkeyPatch


class FakeAlertRepository:
    def __init__(self) -> None:
        self.alerts: dict[str, AlertEntity] = {}
        self.audits: list[AlertAuditEntity] = []

    async def create(
        self,
        *,
        tenant_id: str,
        severity: str,
        message: str,
        domain_id: str | None = None,
        status: str = "new",
    ) -> AlertEntity:
        now = datetime(2026, 4, 6, tzinfo=UTC)
        alert = AlertEntity(
            id=f"alert-{len(self.alerts) + 1}",
            tenant_id=tenant_id,
            domain_id=domain_id,
            severity=severity,
            status=status,
            message=message,
            assignee=None,
            escalation_level=0,
            created_at=now,
            updated_at=now,
        )
        self.alerts[alert.id] = alert
        return alert

    async def get_by_id(self, *, tenant_id: str, alert_id: str) -> AlertEntity | None:
        found = self.alerts.get(alert_id)
        if found is None or found.tenant_id != tenant_id:
            return None
        return found

    async def append_audit(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        action: str,
        actor: str | None = None,
        comment: str | None = None,
        details: dict[str, object] | None = None,
    ) -> AlertAuditEntity:
        audit = AlertAuditEntity(
            id=f"audit-{len(self.audits) + 1}",
            tenant_id=tenant_id,
            alert_id=alert_id,
            action=action,
            actor=actor,
            comment=comment,
            details=details or {},
            created_at=datetime(2026, 4, 6, tzinfo=UTC),
        )
        self.audits.append(audit)
        return audit


class FakeRouter:
    def channels_for(self, *, severity: AlertSeverity) -> tuple[AlertChannel, ...]:
        if severity == AlertSeverity.CRITICAL:
            return (AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SIEM)
        if severity == AlertSeverity.HIGH:
            return (AlertChannel.EMAIL, AlertChannel.SLACK)
        return (AlertChannel.EMAIL,)


class FakeNotifier:
    def __init__(self, *, channel: AlertChannel, delivered: bool, detail: str) -> None:
        self.channel = channel
        self.delivered = delivered
        self.detail = detail
        self.notifications: list[AlertNotification] = []

    async def send(self, *, notification: AlertNotification) -> DispatchResult:
        self.notifications.append(notification)
        return DispatchResult(
            channel=self.channel,
            delivered=self.delivered,
            detail=self.detail,
        )


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


def test_alert_worker_creates_and_dispatches_channels(monkeypatch: MonkeyPatch) -> None:
    fake_repo = FakeAlertRepository()
    email_notifier = FakeNotifier(channel=AlertChannel.EMAIL, delivered=True, detail="sent")
    slack_notifier = FakeNotifier(
        channel=AlertChannel.SLACK,
        delivered=False,
        detail="slack unreachable",
    )
    siem_notifier = FakeNotifier(channel=AlertChannel.SIEM, delivered=True, detail="sent")
    realtime_publisher = FakeRealtimePublisher()

    monkeypatch.setattr(alert_module, "_build_alert_repository", lambda: fake_repo)
    monkeypatch.setattr(alert_module, "_build_router", lambda: FakeRouter())
    monkeypatch.setattr(alert_module, "_build_email_notifier", lambda: email_notifier)
    monkeypatch.setattr(alert_module, "_build_slack_notifier", lambda: slack_notifier)
    monkeypatch.setattr(alert_module, "_build_siem_notifier", lambda: siem_notifier)
    monkeypatch.setattr(alert_module, "_build_realtime_publisher", lambda: realtime_publisher)

    result = asyncio.run(
        alert_module._create_and_dispatch_alert_async(
            payload={
                "tenant_id": "tenant-1",
                "severity": "high",
                "message": "Suspicious source detected",
                "source": "correlation",
            }
        )
    )

    assert result["target_channels"] == 2
    assert result["delivered_channels"] == 1
    assert result["failed_channels"] == 1
    assert len(fake_repo.alerts) == 1
    assert [item.action for item in fake_repo.audits] == [
        "created",
        "dispatch_channel",
        "dispatch_channel",
    ]
    assert [item["event_type"] for item in realtime_publisher.events] == [
        "alert.created",
        "alert.dispatch_channel",
        "alert.dispatch_channel",
    ]


def test_alert_worker_dispatches_existing_alert(monkeypatch: MonkeyPatch) -> None:
    fake_repo = FakeAlertRepository()
    created = asyncio.run(
        fake_repo.create(
            tenant_id="tenant-1",
            severity="medium",
            message="Manual alert",
        )
    )

    email_notifier = FakeNotifier(channel=AlertChannel.EMAIL, delivered=True, detail="sent")
    realtime_publisher = FakeRealtimePublisher()

    monkeypatch.setattr(alert_module, "_build_alert_repository", lambda: fake_repo)
    monkeypatch.setattr(alert_module, "_build_router", lambda: FakeRouter())
    monkeypatch.setattr(alert_module, "_build_email_notifier", lambda: email_notifier)
    monkeypatch.setattr(
        alert_module,
        "_build_slack_notifier",
        lambda: FakeNotifier(channel=AlertChannel.SLACK, delivered=True, detail="sent"),
    )
    monkeypatch.setattr(
        alert_module,
        "_build_siem_notifier",
        lambda: FakeNotifier(channel=AlertChannel.SIEM, delivered=True, detail="sent"),
    )
    monkeypatch.setattr(alert_module, "_build_realtime_publisher", lambda: realtime_publisher)

    result = asyncio.run(
        alert_module._dispatch_existing_alert_async(
            payload={
                "tenant_id": "tenant-1",
                "alert_id": created.id,
                "source": "correlation",
            }
        )
    )

    assert result["not_found"] == 0
    assert result["target_channels"] == 1
    assert result["delivered_channels"] == 1
    assert result["failed_channels"] == 0
    assert [item["event_type"] for item in realtime_publisher.events] == [
        "alert.dispatch_channel",
    ]


def test_alert_worker_reports_not_found_for_unknown_alert(monkeypatch: MonkeyPatch) -> None:
    fake_repo = FakeAlertRepository()

    monkeypatch.setattr(alert_module, "_build_alert_repository", lambda: fake_repo)

    result = asyncio.run(
        alert_module._dispatch_existing_alert_async(
            payload={
                "tenant_id": "tenant-1",
                "alert_id": "missing-alert",
                "source": "correlation",
            }
        )
    )

    assert result["not_found"] == 1
    assert result["target_channels"] == 0
    assert result["delivered_channels"] == 0
    assert result["failed_channels"] == 0
