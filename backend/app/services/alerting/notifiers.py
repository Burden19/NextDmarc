import json
from collections.abc import Awaitable, Callable
from email.message import EmailMessage

import aiosmtplib
import httpx

from .models import AlertChannel, AlertNotification, DispatchResult


class EmailNotifier:
    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        recipients: list[str],
        timeout_seconds: float = 8.0,
        send_email: Callable[..., Awaitable[object]] | None = None,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._sender = sender
        self._recipients = recipients
        self._timeout_seconds = timeout_seconds
        self._send_email = send_email or aiosmtplib.send

    async def send(self, *, notification: AlertNotification) -> DispatchResult:
        if not self._recipients:
            return DispatchResult(
                channel=AlertChannel.EMAIL,
                delivered=False,
                detail="email notifier has no recipients configured",
            )

        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = ", ".join(self._recipients)
        message["Subject"] = f"[{notification.severity.value.upper()}] {notification.title}"
        message.set_content(_notification_text(notification=notification))

        await self._send_email(
            message,
            hostname=self._smtp_host,
            port=self._smtp_port,
            timeout=self._timeout_seconds,
        )

        return DispatchResult(
            channel=AlertChannel.EMAIL,
            delivered=True,
            detail=f"delivered to {len(self._recipients)} recipient(s)",
        )


class SlackWebhookNotifier:
    def __init__(
        self,
        *,
        webhook_url: str,
        timeout_seconds: float = 8.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    async def send(self, *, notification: AlertNotification) -> DispatchResult:
        if not self._webhook_url:
            return DispatchResult(
                channel=AlertChannel.SLACK,
                delivered=False,
                detail="slack webhook url is not configured",
            )

        payload = {"text": _notification_text(notification=notification)}

        if self._http_client is not None:
            response = await self._http_client.post(self._webhook_url, json=payload)
        else:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(self._webhook_url, json=payload)

        if response.status_code >= 400:
            return DispatchResult(
                channel=AlertChannel.SLACK,
                delivered=False,
                detail=f"slack webhook returned status {response.status_code}",
            )

        return DispatchResult(
            channel=AlertChannel.SLACK,
            delivered=True,
            detail="message pushed to slack webhook",
        )


class SiemPushNotifier:
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str = "",
        timeout_seconds: float = 8.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    async def send(self, *, notification: AlertNotification) -> DispatchResult:
        if not self._endpoint:
            return DispatchResult(
                channel=AlertChannel.SIEM,
                delivered=False,
                detail="siem endpoint is not configured",
            )

        payload = {
            "tenant_id": notification.tenant_id,
            "alert_id": notification.alert_id,
            "severity": notification.severity.value,
            "title": notification.title,
            "description": notification.description,
            "source": notification.source,
            "occurred_at": notification.occurred_at,
            "metadata": notification.metadata,
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        if self._http_client is not None:
            response = await self._http_client.post(
                self._endpoint,
                content=json.dumps(payload),
                headers=headers,
            )
        else:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._endpoint,
                    content=json.dumps(payload),
                    headers=headers,
                )

        if response.status_code >= 400:
            return DispatchResult(
                channel=AlertChannel.SIEM,
                delivered=False,
                detail=f"siem endpoint returned status {response.status_code}",
            )

        return DispatchResult(
            channel=AlertChannel.SIEM,
            delivered=True,
            detail="payload pushed to siem endpoint",
        )


def _notification_text(*, notification: AlertNotification) -> str:
    return (
        f"tenant={notification.tenant_id}\n"
        f"alert_id={notification.alert_id}\n"
        f"severity={notification.severity.value}\n"
        f"title={notification.title}\n"
        f"description={notification.description}"
    )
