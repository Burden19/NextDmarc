import asyncio
from typing import Any, Protocol

from celery import Task

from app.core.config import get_settings
from app.repositories.alert_repository import AlertEntity, AlertRepository
from app.services.alerting import (
    AlertChannel,
    AlertNotification,
    AlertRouter,
    AlertSeverity,
    DispatchResult,
    EmailNotifier,
    SiemPushNotifier,
    SlackWebhookNotifier,
    build_router_from_settings,
)
from app.services.alerting.realtime import (
    AlertRealtimePublisher,
    build_alert_realtime_publisher,
)
from app.workers.celery_app import celery_app


class AlertNotifier(Protocol):
    async def send(self, *, notification: AlertNotification) -> DispatchResult: ...


def _build_alert_repository() -> AlertRepository:
    return AlertRepository()


def _build_router() -> AlertRouter:
    return build_router_from_settings()


def _build_email_notifier() -> EmailNotifier:
    settings = get_settings()
    return EmailNotifier(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        sender=settings.alert_email_from,
        recipients=settings.alert_email_recipients,
    )


def _build_slack_notifier() -> SlackWebhookNotifier:
    settings = get_settings()
    return SlackWebhookNotifier(
        webhook_url=settings.alert_slack_webhook_url,
        timeout_seconds=settings.alert_siem_timeout_seconds,
    )


def _build_siem_notifier() -> SiemPushNotifier:
    settings = get_settings()
    return SiemPushNotifier(
        endpoint=settings.alert_siem_endpoint,
        api_key=settings.alert_siem_api_key,
        timeout_seconds=settings.alert_siem_timeout_seconds,
    )


def _build_realtime_publisher() -> AlertRealtimePublisher:
    return build_alert_realtime_publisher()


def _retry_delay_seconds(retry_count: int) -> int:
    bounded_retry = retry_count if retry_count >= 0 else 0
    delay = 10 * (2**bounded_retry)
    return 300 if delay > 300 else delay


@celery_app.task(bind=True, name="app.workers.tasks.alert.create_and_dispatch_alert", max_retries=5)
def create_and_dispatch_alert(
    self: Task,
    **payload: Any,
) -> dict[str, int | str]:
    try:
        return asyncio.run(_create_and_dispatch_alert_async(payload=payload))
    except Exception as exc:
        countdown = _retry_delay_seconds(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


@celery_app.task(bind=True, name="app.workers.tasks.alert.dispatch_existing_alert", max_retries=5)
def dispatch_existing_alert(
    self: Task,
    **payload: Any,
) -> dict[str, int | str]:
    try:
        return asyncio.run(_dispatch_existing_alert_async(payload=payload))
    except Exception as exc:
        countdown = _retry_delay_seconds(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


async def _create_and_dispatch_alert_async(*, payload: dict[str, Any]) -> dict[str, int | str]:
    tenant_id = str(payload.get("tenant_id", "")).strip()
    message = str(payload.get("message", "")).strip()
    if not tenant_id:
        raise ValueError("tenant_id is required")
    if not message:
        raise ValueError("message is required")

    severity = _parse_severity(payload.get("severity"))
    actor = _normalize_optional(payload.get("actor")) or "worker.alert"
    source = _normalize_optional(payload.get("source")) or "pipeline"

    repository = _build_alert_repository()
    created = await repository.create(
        tenant_id=tenant_id,
        severity=severity.value,
        message=message,
        domain_id=_normalize_optional(payload.get("domain_id")),
        status="new",
    )
    await repository.append_audit(
        tenant_id=tenant_id,
        alert_id=created.id,
        action="created",
        actor=actor,
        details={"source": source},
    )
    await _publish_realtime_event(
        tenant_id=tenant_id,
        event_type="alert.created",
        alert_id=created.id,
        payload={
            "severity": created.severity,
            "status": created.status,
            "message": created.message,
            "source": source,
        },
    )

    dispatch = await _dispatch_alert_channels(
        repository=repository,
        alert=created,
        source=source,
    )
    return {
        "tenant_id": tenant_id,
        "alert_id": created.id,
        "target_channels": dispatch["target_channels"],
        "delivered_channels": dispatch["delivered_channels"],
        "failed_channels": dispatch["failed_channels"],
    }


async def _dispatch_existing_alert_async(*, payload: dict[str, Any]) -> dict[str, int | str]:
    tenant_id = str(payload.get("tenant_id", "")).strip()
    alert_id = str(payload.get("alert_id", "")).strip()
    if not tenant_id:
        raise ValueError("tenant_id is required")
    if not alert_id:
        raise ValueError("alert_id is required")

    source = _normalize_optional(payload.get("source")) or "pipeline"
    repository = _build_alert_repository()
    found = await repository.get_by_id(tenant_id=tenant_id, alert_id=alert_id)
    if found is None:
        return {
            "tenant_id": tenant_id,
            "alert_id": alert_id,
            "target_channels": 0,
            "delivered_channels": 0,
            "failed_channels": 0,
            "not_found": 1,
        }

    dispatch = await _dispatch_alert_channels(
        repository=repository,
        alert=found,
        source=source,
    )
    return {
        "tenant_id": tenant_id,
        "alert_id": alert_id,
        "target_channels": dispatch["target_channels"],
        "delivered_channels": dispatch["delivered_channels"],
        "failed_channels": dispatch["failed_channels"],
        "not_found": 0,
    }


async def _dispatch_alert_channels(
    *,
    repository: AlertRepository,
    alert: AlertEntity,
    source: str,
) -> dict[str, int]:
    router = _build_router()
    severity = _parse_severity(alert.severity)
    channels = router.channels_for(severity=severity)

    if not channels:
        await repository.append_audit(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            action="dispatch_skipped",
            actor="worker.alert",
            comment="no channels mapped for severity",
            details={"source": source, "severity": severity.value},
        )
        return {
            "target_channels": 0,
            "delivered_channels": 0,
            "failed_channels": 0,
        }

    notifier_by_channel: dict[AlertChannel, AlertNotifier] = {
        AlertChannel.EMAIL: _build_email_notifier(),
        AlertChannel.SLACK: _build_slack_notifier(),
        AlertChannel.SIEM: _build_siem_notifier(),
    }

    delivered = 0
    failed = 0
    for channel in channels:
        notification = AlertNotification(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            severity=severity,
            title=f"Alert {alert.id}",
            description=alert.message,
            source=source,
            metadata={
                "status": alert.status,
                "assignee": alert.assignee,
            },
        )
        result = await _send_with_guard(
            notifier=notifier_by_channel[channel],
            channel=channel,
            notification=notification,
        )
        if result.delivered:
            delivered += 1
        else:
            failed += 1

        await repository.append_audit(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            action="dispatch_channel",
            actor="worker.alert",
            comment=result.detail,
            details={
                "source": source,
                "channel": channel.value,
                "delivered": result.delivered,
            },
        )
        await _publish_realtime_event(
            tenant_id=alert.tenant_id,
            event_type="alert.dispatch_channel",
            alert_id=alert.id,
            payload={
                "channel": channel.value,
                "delivered": result.delivered,
                "detail": result.detail,
                "source": source,
            },
        )

    return {
        "target_channels": len(channels),
        "delivered_channels": delivered,
        "failed_channels": failed,
    }


async def _send_with_guard(
    *,
    notifier: AlertNotifier,
    channel: AlertChannel,
    notification: AlertNotification,
) -> DispatchResult:
    try:
        return await notifier.send(notification=notification)
    except Exception as exc:
        return DispatchResult(
            channel=channel,
            delivered=False,
            detail=f"dispatch error: {type(exc).__name__}",
        )


def _parse_severity(value: object) -> AlertSeverity:
    if isinstance(value, AlertSeverity):
        return value
    normalized = str(value).strip().lower()
    try:
        return AlertSeverity(normalized)
    except ValueError:
        return AlertSeverity.MEDIUM


def _normalize_optional(value: object) -> str | None:
    normalized = str(value).strip() if value is not None else ""
    return normalized if normalized else None


async def _publish_realtime_event(
    *,
    tenant_id: str,
    event_type: str,
    alert_id: str,
    payload: dict[str, object],
) -> None:
    publisher = _build_realtime_publisher()
    try:
        await publisher.publish_event(
            tenant_id=tenant_id,
            event_type=event_type,
            alert_id=alert_id,
            payload=payload,
        )
    except Exception:
        return
