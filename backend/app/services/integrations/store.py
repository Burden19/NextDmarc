from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Literal
from uuid import UUID, uuid4

IntegrationKind = Literal["email", "slack", "siem"]


@dataclass(slots=True)
class IntegrationRecord:
    id: UUID
    tenant_id: UUID
    name: str
    kind: IntegrationKind
    config: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class IntegrationTestResult:
    integration_id: UUID
    status: str
    detail: str


class InMemoryIntegrationStore:
    def __init__(self) -> None:
        self._records: dict[UUID, IntegrationRecord] = {}

    def create(
        self,
        *,
        tenant_id: UUID,
        name: str,
        kind: IntegrationKind,
        config: dict[str, Any],
        enabled: bool = True,
    ) -> IntegrationRecord:
        now = datetime.now(tz=UTC)
        record = IntegrationRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            kind=kind,
            config=dict(config),
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        return record

    def list(self, *, tenant_id: UUID) -> list[IntegrationRecord]:
        return [item for item in self._records.values() if item.tenant_id == tenant_id]

    def get(self, *, tenant_id: UUID, integration_id: UUID) -> IntegrationRecord | None:
        found = self._records.get(integration_id)
        if found is None or found.tenant_id != tenant_id:
            return None
        return found

    def update(
        self,
        *,
        tenant_id: UUID,
        integration_id: UUID,
        name: str | None,
        config: dict[str, Any] | None,
        enabled: bool | None,
    ) -> IntegrationRecord | None:
        found = self.get(tenant_id=tenant_id, integration_id=integration_id)
        if found is None:
            return None

        if name is not None:
            found.name = name
        if config is not None:
            found.config = dict(config)
        if enabled is not None:
            found.enabled = enabled
        found.updated_at = datetime.now(tz=UTC)
        return found

    def delete(self, *, tenant_id: UUID, integration_id: UUID) -> bool:
        found = self.get(tenant_id=tenant_id, integration_id=integration_id)
        if found is None:
            return False
        del self._records[integration_id]
        return True

    def test_connector(
        self,
        *,
        tenant_id: UUID,
        integration_id: UUID,
    ) -> IntegrationTestResult | None:
        found = self.get(tenant_id=tenant_id, integration_id=integration_id)
        if found is None:
            return None

        status, detail = _validate_connector(kind=found.kind, config=found.config)
        found.updated_at = datetime.now(tz=UTC)
        return IntegrationTestResult(
            integration_id=found.id,
            status=status,
            detail=detail,
        )


def _validate_connector(*, kind: IntegrationKind, config: dict[str, Any]) -> tuple[str, str]:
    if kind == "email":
        sender = _as_non_empty_string(config.get("sender"))
        recipients = config.get("recipients")
        has_recipient = isinstance(recipients, list) and any(
            _as_non_empty_string(item) for item in recipients
        )
        if sender and has_recipient:
            return "ok", "email integration settings look valid"
        return "failed", "email connector requires sender and at least one recipient"

    if kind == "slack":
        webhook_url = _as_non_empty_string(config.get("webhook_url"))
        if webhook_url and webhook_url.startswith("http"):
            return "ok", "slack webhook configuration looks valid"
        return "failed", "slack connector requires a valid webhook_url"

    endpoint = _as_non_empty_string(config.get("endpoint"))
    if endpoint and endpoint.startswith("http"):
        return "ok", "siem endpoint configuration looks valid"
    return "failed", "siem connector requires a valid endpoint"


def _as_non_empty_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


@lru_cache(maxsize=1)
def get_integration_store() -> InMemoryIntegrationStore:
    return InMemoryIntegrationStore()


def reset_integration_store_for_tests() -> None:
    get_integration_store.cache_clear()
