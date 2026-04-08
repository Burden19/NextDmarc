from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings


def tenant_channel_for(*, tenant_id: str) -> str:
    return f"alerts:tenant:{tenant_id}"


class AlertRealtimePublisher:
    def __init__(self, *, redis_url: str) -> None:
        self._redis_url = redis_url

    async def publish_event(
        self,
        *,
        tenant_id: str,
        event_type: str,
        alert_id: str,
        payload: dict[str, Any],
    ) -> None:
        envelope = {
            "type": event_type,
            "tenant_id": tenant_id,
            "alert_id": alert_id,
            "published_at": datetime.now(tz=UTC).isoformat(),
            "payload": payload,
        }

        client = Redis.from_url(self._redis_url, decode_responses=True)
        try:
            await client.publish(
                tenant_channel_for(tenant_id=tenant_id),
                json.dumps(envelope),
            )
        finally:
            await client.aclose()


class AlertRealtimeStream:
    def __init__(self, *, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: Redis | None = None
        self._pubsub: Any | None = None
        self._tenant_id: str | None = None

    async def connect(self) -> None:
        if self._redis is not None:
            return
        self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()

    async def subscribe(self, *, tenant_id: str) -> None:
        if self._pubsub is None:
            raise RuntimeError("alert realtime stream is not connected")
        self._tenant_id = tenant_id
        await self._pubsub.subscribe(tenant_channel_for(tenant_id=tenant_id))

    async def next_event(self, *, timeout_seconds: float) -> dict[str, Any] | None:
        if self._pubsub is None:
            raise RuntimeError("alert realtime stream is not connected")

        message = await self._pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=timeout_seconds,
        )
        if message is None:
            return None

        data = message.get("data")
        if isinstance(data, bytes):
            text = data.decode("utf-8", errors="replace")
        elif isinstance(data, str):
            text = data
        else:
            return None

        payload = _json_object_or_none(text)
        if payload is None:
            return {
                "type": "alert.raw",
                "tenant_id": self._tenant_id or "",
                "payload": {"raw": text},
            }

        if "tenant_id" not in payload and self._tenant_id is not None:
            payload["tenant_id"] = self._tenant_id
        return payload

    async def close(self) -> None:
        if self._pubsub is not None:
            close_method = getattr(self._pubsub, "aclose", None)
            if callable(close_method):
                await close_method()
            else:
                fallback = getattr(self._pubsub, "close", None)
                if callable(fallback):
                    maybe_awaitable = fallback()
                    if inspect.isawaitable(maybe_awaitable):
                        await maybe_awaitable
            self._pubsub = None

        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


def build_alert_realtime_publisher() -> AlertRealtimePublisher:
    settings = get_settings()
    return AlertRealtimePublisher(redis_url=settings.redis_url)


def build_alert_realtime_stream() -> AlertRealtimeStream:
    settings = get_settings()
    return AlertRealtimeStream(redis_url=settings.redis_url)


def _json_object_or_none(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    return {str(key): value for key, value in parsed.items()}
