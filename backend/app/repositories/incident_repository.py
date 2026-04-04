from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text

from app.db.session import get_session_factory


@dataclass(slots=True)
class IncidentEntity:
    id: str
    tenant_id: str
    severity: str
    status: str
    message: str
    created_at: datetime
    updated_at: datetime


class IncidentRepository:
    async def list(self, *, tenant_id: str, limit: int = 100) -> list[IncidentEntity]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            rows = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, severity, status, message, created_at, updated_at
                    FROM alerts
                    WHERE tenant_id = :tenant_id::uuid
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"tenant_id": tenant_id, "limit": limit},
            )
            return [_map_incident(row) for row in rows.mappings().all()]

    async def get_by_id(self, *, tenant_id: str, incident_id: str) -> IncidentEntity | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, severity, status, message, created_at, updated_at
                    FROM alerts
                    WHERE tenant_id = :tenant_id::uuid AND id = :incident_id::uuid
                    """
                ),
                {"tenant_id": tenant_id, "incident_id": incident_id},
            )
            mapped = row.mappings().first()
            if mapped is None:
                return None
            return _map_incident(mapped)

    async def close(self, *, tenant_id: str, incident_id: str) -> IncidentEntity | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.execute(
                text(
                    """
                    UPDATE alerts
                    SET status = 'closed', updated_at = now()
                    WHERE tenant_id = :tenant_id::uuid AND id = :incident_id::uuid
                    RETURNING id, tenant_id, severity, status, message, created_at, updated_at
                    """
                ),
                {"tenant_id": tenant_id, "incident_id": incident_id},
            )
            mapped = row.mappings().first()
            if mapped is None:
                return None
            await session.commit()
            return _map_incident(mapped)


def _map_incident(row: object) -> IncidentEntity:
    if not isinstance(row, dict):
        row = dict(row)
    return IncidentEntity(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        severity=str(row["severity"]),
        status=str(row["status"]),
        message=str(row["message"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
