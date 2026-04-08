from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from app.db.session import get_session_factory
from app.services.correlation.classifier import CorrelationClassification


@dataclass(slots=True)
class CreatedIncident:
    id: str
    tenant_id: str
    severity: str
    message: str


class IncidentCreator:
    async def create_incidents(
        self,
        *,
        tenant_id: str,
        classifications: list[CorrelationClassification],
    ) -> int:
        created = await self.create_incidents_with_details(
            tenant_id=tenant_id,
            classifications=classifications,
        )
        return len(created)

    async def create_incidents_with_details(
        self,
        *,
        tenant_id: str,
        classifications: list[CorrelationClassification],
    ) -> list[CreatedIncident]:
        if not classifications:
            return []

        session_factory = get_session_factory()
        created: list[CreatedIncident] = []
        async with session_factory() as session:
            for item in classifications:
                alert_id = str(uuid4())
                await session.execute(
                    text(
                        """
                        INSERT INTO alerts (
                            id,
                            tenant_id,
                            domain_id,
                            severity,
                            status,
                            message,
                            created_at,
                            updated_at
                        ) VALUES (
                            :id,
                            :tenant_id::uuid,
                            NULL,
                            :severity,
                            'new',
                            :message,
                            :created_at,
                            :updated_at
                        )
                        """
                    ),
                    {
                        "id": alert_id,
                        "tenant_id": tenant_id,
                        "severity": item.severity,
                        "message": item.message,
                        "created_at": datetime.now(tz=UTC),
                        "updated_at": datetime.now(tz=UTC),
                    },
                )
                created.append(
                    CreatedIncident(
                        id=alert_id,
                        tenant_id=tenant_id,
                        severity=item.severity,
                        message=item.message,
                    )
                )
            await session.commit()

        return created
