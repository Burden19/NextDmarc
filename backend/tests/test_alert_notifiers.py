import json

import httpx
import pytest
from app.services.alerting.models import AlertNotification, AlertSeverity
from app.services.alerting.notifiers import EmailNotifier, SiemPushNotifier, SlackWebhookNotifier


def _build_notification() -> AlertNotification:
    return AlertNotification(
        tenant_id="tenant-1",
        alert_id="alert-1",
        severity=AlertSeverity.HIGH,
        title="Spoofing spike detected",
        description="DKIM failures increased significantly for the domain.",
        source="analysis",
        occurred_at="2026-04-06T10:00:00Z",
        metadata={"domain": "example.com"},
    )


@pytest.mark.asyncio
async def test_email_notifier_sends_to_configured_recipients() -> None:
    sent = {"count": 0, "subject": "", "to": ""}

    async def fake_send(message, *, hostname: str, port: int, timeout: float):
        sent["count"] += 1
        sent["subject"] = str(message["Subject"])
        sent["to"] = str(message["To"])
        assert hostname == "smtp.local"
        assert port == 2525
        assert timeout == 7.0

    notifier = EmailNotifier(
        smtp_host="smtp.local",
        smtp_port=2525,
        sender="alerts@example.test",
        recipients=["soc@example.test"],
        timeout_seconds=7.0,
        send_email=fake_send,
    )

    result = await notifier.send(notification=_build_notification())

    assert result.delivered is True
    assert sent["count"] == 1
    assert "SPOOFING SPIKE DETECTED" in sent["subject"].upper()
    assert "soc@example.test" in sent["to"]


@pytest.mark.asyncio
async def test_slack_notifier_posts_webhook_payload() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        assert request.url.path == "/hooks/alerts"
        payload = json.loads(request.content.decode("utf-8"))
        assert "tenant=tenant-1" in payload["text"]
        return httpx.Response(status_code=200, json={"ok": True})

    async with httpx.AsyncClient(
        base_url="http://mock.local", transport=httpx.MockTransport(handler)
    ) as client:
        notifier = SlackWebhookNotifier(
            webhook_url="/hooks/alerts",
            http_client=client,
        )
        result = await notifier.send(notification=_build_notification())

    assert result.delivered is True
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_siem_notifier_pushes_json_payload() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        assert request.url.path == "/siem/events"
        assert request.headers.get("Authorization") == "Bearer token-1"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["alert_id"] == "alert-1"
        assert payload["severity"] == "high"
        return httpx.Response(status_code=202, json={"accepted": True})

    async with httpx.AsyncClient(
        base_url="http://mock.local", transport=httpx.MockTransport(handler)
    ) as client:
        notifier = SiemPushNotifier(
            endpoint="/siem/events",
            api_key="token-1",
            http_client=client,
        )
        result = await notifier.send(notification=_build_notification())

    assert result.delivered is True
    assert calls["count"] == 1
