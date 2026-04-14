from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.db.session import get_session_factory
from app.repositories.pagination import Page, build_offset_limit


@dataclass(slots=True)
class ReportEntity:
    id: str
    tenant_id: str
    domain_id: str
    report_id: str
    reporter_org: str
    date_range_begin: datetime
    date_range_end: datetime
    created_at: datetime


class ReportRepository:
    async def get_by_id(self, *, tenant_id: str, report_db_id: str) -> ReportEntity | None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, domain_id, report_id, reporter_org,
                           date_range_begin, date_range_end, created_at
                    FROM dmarc_reports
                    WHERE tenant_id = :tenant_id AND id = :id
                    """
                ),
                {"tenant_id": tenant_id, "id": report_db_id},
            )
            row = result.mappings().first()
            if row is None:
                return None
            return self._map_row(dict(row))

    async def list(self, *, tenant_id: str, page: int, page_size: int) -> Page[ReportEntity]:
        offset, limit = build_offset_limit(page=page, page_size=page_size)

        session_factory = get_session_factory()
        async with session_factory() as session:
            total_result = await session.execute(
                text("SELECT COUNT(*) FROM dmarc_reports WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id},
            )
            total = int(total_result.scalar_one())

            result = await session.execute(
                text(
                    """
                    SELECT id, tenant_id, domain_id, report_id, reporter_org,
                           date_range_begin, date_range_end, created_at
                    FROM dmarc_reports
                          WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    OFFSET :offset LIMIT :limit
                    """
                ),
                {"tenant_id": tenant_id, "offset": offset, "limit": limit},
            )
            rows = result.mappings().all()

        return Page(
            items=[self._map_row(dict(row)) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def delete(self, *, tenant_id: str, report_db_id: str) -> bool:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    """
                    DELETE FROM dmarc_reports
                    WHERE tenant_id = :tenant_id AND id = :id
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "id": report_db_id},
            )
            deleted = result.scalar_one_or_none()
            await session.commit()
            return deleted is not None

    def _map_row(self, row: dict[str, Any]) -> ReportEntity:
        return ReportEntity(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            domain_id=str(row["domain_id"]),
            report_id=str(row["report_id"]),
            reporter_org=str(row["reporter_org"]),
            date_range_begin=row["date_range_begin"],
            date_range_end=row["date_range_end"],
            created_at=row["created_at"],
        )
