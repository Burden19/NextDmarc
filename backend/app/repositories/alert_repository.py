from __future__ import annotations

import builtins
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory
from app.repositories.pagination import Page, build_offset_limit


@dataclass(slots=True)
class AlertEntity:
    id: str
    tenant_id: str
    domain_id: str | None
    severity: str
    status: str
    message: str
    assignee: str | None
    escalation_level: int
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class AlertAuditEntity:
    id: str
    tenant_id: str
    alert_id: str
    action: str
    actor: str | None
    comment: str | None
    details: dict[str, object]
    created_at: datetime


@dataclass(slots=True)
class AlertTriageResult:
    alert: AlertEntity
    audit: AlertAuditEntity


class AlertRepository:
    async def create(
        self,
        *,
        tenant_id: str,
        severity: str,
        message: str,
        domain_id: str | None = None,
        status: str = "new",
    ) -> AlertEntity:
        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.execute(
                text(
                    """
                    INSERT INTO alerts (
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    ) VALUES (
                        :id,
                        :tenant_id::uuid,
                        :domain_id::uuid,
                        :severity,
                        :status,
                        :message,
                        NULL,
                        0,
                        now(),
                        now()
                    )
                    RETURNING
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    """
                ),
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "domain_id": domain_id,
                    "severity": severity,
                    "status": status,
                    "message": message,
                },
            )
            mapped = row.mappings().first()
            if mapped is None:
                raise RuntimeError("failed to create alert")
            await session.commit()
            return _map_alert(cast(Mapping[str, Any], mapped))

    async def list(self, *, tenant_id: str, limit: int = 100) -> list[AlertEntity]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            rows = await session.execute(
                text(
                    """
                    SELECT
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    FROM alerts
                    WHERE tenant_id = :tenant_id::uuid
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "limit": limit,
                },
            )
            return [_map_alert(cast(Mapping[str, Any], item)) for item in rows.mappings().all()]

    async def list_paginated(
        self,
        *,
        tenant_id: str,
        page: int,
        page_size: int,
        status: str | None = None,
        severity: str | None = None,
    ) -> Page[AlertEntity]:
        offset, limit = build_offset_limit(page=page, page_size=page_size)

        where_clauses = ["tenant_id = :tenant_id::uuid"]
        parameters: dict[str, object] = {
            "tenant_id": tenant_id,
            "offset": offset,
            "limit": limit,
        }

        normalized_status = (status or "").strip().lower()
        if normalized_status:
            where_clauses.append("LOWER(status) = :status")
            parameters["status"] = normalized_status

        normalized_severity = (severity or "").strip().lower()
        if normalized_severity:
            where_clauses.append("LOWER(severity) = :severity")
            parameters["severity"] = normalized_severity

        where_sql = " AND ".join(where_clauses)

        session_factory = get_session_factory()
        async with session_factory() as session:
            total_result = await session.execute(
                text(f"SELECT COUNT(*) FROM alerts WHERE {where_sql}"),
                parameters,
            )
            total = int(total_result.scalar_one())

            rows = await session.execute(
                text(
                    f"""
                    SELECT
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    FROM alerts
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    OFFSET :offset LIMIT :limit
                    """
                ),
                parameters,
            )
            items = [_map_alert(cast(Mapping[str, Any], item)) for item in rows.mappings().all()]

        return Page(items=items, total=total, page=page, page_size=page_size)

    async def get_by_id(self, *, tenant_id: str, alert_id: str) -> AlertEntity | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.execute(
                text(
                    """
                    SELECT
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    FROM alerts
                    WHERE tenant_id = :tenant_id::uuid AND id = :alert_id::uuid
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "alert_id": alert_id,
                },
            )
            mapped = row.mappings().first()
            if mapped is None:
                return None
            return _map_alert(cast(Mapping[str, Any], mapped))

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
        session_factory = get_session_factory()
        async with session_factory() as session:
            audit = await _insert_audit(
                session=session,
                tenant_id=tenant_id,
                alert_id=alert_id,
                action=action,
                actor=actor,
                comment=comment,
                details=details,
            )
            await session.commit()
            return audit

    async def list_audit(self, *, tenant_id: str, alert_id: str) -> builtins.list[AlertAuditEntity]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            rows = await session.execute(
                text(
                    """
                    SELECT
                        id,
                        tenant_id,
                        alert_id,
                        action,
                        actor,
                        comment,
                        details,
                        created_at
                    FROM alert_audit_logs
                    WHERE tenant_id = :tenant_id::uuid AND alert_id = :alert_id::uuid
                    ORDER BY created_at ASC
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "alert_id": alert_id,
                },
            )
            return [_map_audit(cast(Mapping[str, Any], item)) for item in rows.mappings().all()]

    async def update_status(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        status: str,
        actor: str | None = None,
        comment: str | None = None,
    ) -> AlertTriageResult | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.execute(
                text(
                    """
                    UPDATE alerts
                    SET status = :status, updated_at = now()
                    WHERE tenant_id = :tenant_id::uuid AND id = :alert_id::uuid
                    RETURNING
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "alert_id": alert_id,
                    "status": status,
                },
            )
            mapped = row.mappings().first()
            if mapped is None:
                return None

            audit = await _insert_audit(
                session=session,
                tenant_id=tenant_id,
                alert_id=alert_id,
                action="status_update",
                actor=actor,
                comment=comment,
                details={"status": status},
            )
            await session.commit()
            return AlertTriageResult(alert=_map_alert(cast(Mapping[str, Any], mapped)), audit=audit)

    async def assign(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        assignee: str,
        actor: str | None = None,
        comment: str | None = None,
    ) -> AlertTriageResult | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.execute(
                text(
                    """
                    UPDATE alerts
                    SET assignee = :assignee, updated_at = now()
                    WHERE tenant_id = :tenant_id::uuid AND id = :alert_id::uuid
                    RETURNING
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "alert_id": alert_id,
                    "assignee": assignee,
                },
            )
            mapped = row.mappings().first()
            if mapped is None:
                return None

            audit = await _insert_audit(
                session=session,
                tenant_id=tenant_id,
                alert_id=alert_id,
                action="assign",
                actor=actor,
                comment=comment,
                details={"assignee": assignee},
            )
            await session.commit()
            return AlertTriageResult(alert=_map_alert(cast(Mapping[str, Any], mapped)), audit=audit)

    async def add_comment(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        comment: str,
        actor: str | None = None,
    ) -> AlertTriageResult | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.execute(
                text(
                    """
                    UPDATE alerts
                    SET updated_at = now()
                    WHERE tenant_id = :tenant_id::uuid AND id = :alert_id::uuid
                    RETURNING
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "alert_id": alert_id,
                },
            )
            mapped = row.mappings().first()
            if mapped is None:
                return None

            audit = await _insert_audit(
                session=session,
                tenant_id=tenant_id,
                alert_id=alert_id,
                action="comment",
                actor=actor,
                comment=comment,
                details={},
            )
            await session.commit()
            return AlertTriageResult(alert=_map_alert(cast(Mapping[str, Any], mapped)), audit=audit)

    async def escalate(
        self,
        *,
        tenant_id: str,
        alert_id: str,
        actor: str | None = None,
        comment: str | None = None,
        target_severity: str | None = None,
    ) -> AlertTriageResult | None:
        current = await self.get_by_id(tenant_id=tenant_id, alert_id=alert_id)
        if current is None:
            return None

        next_severity = target_severity or _next_severity(current.severity)
        next_level = current.escalation_level + 1

        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.execute(
                text(
                    """
                    UPDATE alerts
                    SET
                        severity = :severity,
                        escalation_level = :escalation_level,
                        updated_at = now()
                    WHERE tenant_id = :tenant_id::uuid AND id = :alert_id::uuid
                    RETURNING
                        id,
                        tenant_id,
                        domain_id,
                        severity,
                        status,
                        message,
                        assignee,
                        escalation_level,
                        created_at,
                        updated_at
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "alert_id": alert_id,
                    "severity": next_severity,
                    "escalation_level": next_level,
                },
            )
            mapped = row.mappings().first()
            if mapped is None:
                return None

            audit = await _insert_audit(
                session=session,
                tenant_id=tenant_id,
                alert_id=alert_id,
                action="escalate",
                actor=actor,
                comment=comment,
                details={
                    "from_severity": current.severity,
                    "to_severity": next_severity,
                    "escalation_level": next_level,
                },
            )
            await session.commit()
            return AlertTriageResult(alert=_map_alert(cast(Mapping[str, Any], mapped)), audit=audit)


async def _insert_audit(
    *,
    session: AsyncSession,
    tenant_id: str,
    alert_id: str,
    action: str,
    actor: str | None,
    comment: str | None,
    details: dict[str, object] | None,
) -> AlertAuditEntity:
    details_json = json.dumps(details or {})
    row = await session.execute(
        text(
            """
            INSERT INTO alert_audit_logs (
                id,
                tenant_id,
                alert_id,
                action,
                actor,
                comment,
                details,
                created_at
            ) VALUES (
                :id,
                :tenant_id::uuid,
                :alert_id::uuid,
                :action,
                :actor,
                :comment,
                :details::jsonb,
                now()
            )
            RETURNING
                id,
                tenant_id,
                alert_id,
                action,
                actor,
                comment,
                details,
                created_at
            """
        ),
        {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "alert_id": alert_id,
            "action": action,
            "actor": actor,
            "comment": comment,
            "details": details_json,
        },
    )
    mapped = row.mappings().first()
    if mapped is None:
        raise RuntimeError("failed to append alert audit")
    return _map_audit(cast(Mapping[str, Any], mapped))


def _map_alert(row: Mapping[str, Any]) -> AlertEntity:
    return AlertEntity(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        domain_id=None if row["domain_id"] is None else str(row["domain_id"]),
        severity=str(row["severity"]),
        status=str(row["status"]),
        message=str(row["message"]),
        assignee=None if row["assignee"] is None else str(row["assignee"]),
        escalation_level=int(row["escalation_level"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _map_audit(row: Mapping[str, Any]) -> AlertAuditEntity:
    return AlertAuditEntity(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        alert_id=str(row["alert_id"]),
        action=str(row["action"]),
        actor=None if row["actor"] is None else str(row["actor"]),
        comment=None if row["comment"] is None else str(row["comment"]),
        details=_as_dict(row["details"]),
        created_at=row["created_at"],
    )


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return {str(k): v for k, v in parsed.items()}
    return {}


def _next_severity(current: str) -> str:
    levels = ("low", "medium", "high", "critical")
    normalized = current.strip().lower()
    if normalized not in levels:
        return "critical"
    index = levels.index(normalized)
    if index >= len(levels) - 1:
        return levels[-1]
    return levels[index + 1]
