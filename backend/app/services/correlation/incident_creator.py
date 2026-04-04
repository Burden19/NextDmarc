from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from app.db.session import get_session_factory
from app.services.correlation.classifier import CorrelationClassification


class IncidentCreator:
    async def create_incidents(
        self,
        *,
        tenant_id: str,
        classifications: list[CorrelationClassification],
    ) -> int:
        if not classifications:
            return 0

        session_factory = get_session_factory()
        created_count = 0
        async with session_factory() as session:
            for item in classifications:
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
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "severity": item.severity,
                        "message": item.message,
                        "created_at": datetime.now(tz=UTC),
                        "updated_at": datetime.now(tz=UTC),
                    },
                )
                created_count += 1
            await session.commit()

        return created_count
