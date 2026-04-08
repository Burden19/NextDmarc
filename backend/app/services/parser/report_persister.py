from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory
from app.services.parser.dmarc_parser import DmarcParsedReport


class ReportPersister:
    async def persist_report(self, *, tenant_id: str, parsed: DmarcParsedReport) -> str:
        tenant_uuid = UUID(tenant_id)
        session_factory = get_session_factory()

        async with session_factory() as session:
            domain_id = await self._ensure_domain(
                session=session,
                tenant_id=tenant_uuid,
                fqdn=parsed.policy_domain,
            )

            report_id = await self._upsert_report(
                session=session,
                tenant_id=tenant_uuid,
                domain_id=domain_id,
                parsed=parsed,
            )

            for record in parsed.records:
                await session.execute(
                    text(
                        """
                        INSERT INTO sources (id, tenant_id, ip, first_seen, last_seen)
                        VALUES (:id, :tenant_id::uuid, :ip::inet, now(), now())
                        ON CONFLICT (tenant_id, ip)
                        DO UPDATE SET last_seen = now()
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "tenant_id": str(tenant_uuid),
                        "ip": record.source_ip,
                    },
                )

            await session.commit()
            return report_id

    async def _ensure_domain(self, *, session: AsyncSession, tenant_id: UUID, fqdn: str) -> str:
        domain_id = str(uuid4())
        result = await session.execute(
            text(
                """
                INSERT INTO domains (id, tenant_id, fqdn, status, created_at, updated_at)
                VALUES (:id, :tenant_id::uuid, :fqdn, 'active', now(), now())
                ON CONFLICT (tenant_id, fqdn)
                DO UPDATE SET updated_at = now()
                RETURNING id
                """
            ),
            {
                "id": domain_id,
                "tenant_id": str(tenant_id),
                "fqdn": fqdn,
            },
        )
        found = result.scalar_one()
        return str(found)

    async def _upsert_report(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        domain_id: str,
        parsed: DmarcParsedReport,
    ) -> str:
        report_pk = str(uuid4())
        result = await session.execute(
            text(
                """
                INSERT INTO dmarc_reports (
                    id,
                    tenant_id,
                    domain_id,
                    report_id,
                    reporter_org,
                    date_range_begin,
                    date_range_end,
                    created_at
                )
                VALUES (
                    :id,
                    :tenant_id::uuid,
                    :domain_id::uuid,
                    :report_id,
                    :reporter_org,
                    :date_range_begin,
                    :date_range_end,
                    :created_at
                )
                ON CONFLICT (tenant_id, report_id)
                DO UPDATE SET
                    domain_id = EXCLUDED.domain_id,
                    reporter_org = EXCLUDED.reporter_org,
                    date_range_begin = EXCLUDED.date_range_begin,
                    date_range_end = EXCLUDED.date_range_end
                RETURNING id
                """
            ),
            {
                "id": report_pk,
                "tenant_id": str(tenant_id),
                "domain_id": domain_id,
                "report_id": parsed.report_id,
                "reporter_org": parsed.provider_org_name,
                "date_range_begin": parsed.date_range_begin,
                "date_range_end": parsed.date_range_end,
                "created_at": datetime.now(tz=UTC),
            },
        )
        found = result.scalar_one()
        return str(found)
