"""Initial core tables for tenant/auth/domain/report/source/alert.

Revision ID: 20260325_01
Revises:
Create Date: 2026-03-25 10:00:00

"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260325_01"
down_revision = None
branch_labels = None
depends_on = None


def _ts_column(name: str) -> sa.Column[Any]:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def _enable_tenant_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table_name}_tenant_isolation
        ON {table_name}
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        """
    )


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _ts_column("created_at"),
        _ts_column("updated_at"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _ts_column("created_at"),
        _ts_column("updated_at"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_users_tenant_id_tenants"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fqdn", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        _ts_column("created_at"),
        _ts_column("updated_at"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_domains_tenant_id_tenants"),
        sa.UniqueConstraint("tenant_id", "fqdn", name="uq_domains_tenant_id_fqdn"),
    )

    op.create_table(
        "dmarc_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", sa.String(length=255), nullable=False),
        sa.Column("reporter_org", sa.String(length=255), nullable=False),
        sa.Column("date_range_begin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_range_end", sa.DateTime(timezone=True), nullable=False),
        _ts_column("created_at"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_dmarc_reports_tenant_id_tenants"
        ),
        sa.ForeignKeyConstraint(
            ["domain_id"], ["domains.id"], name="fk_dmarc_reports_domain_id_domains"
        ),
        sa.UniqueConstraint("tenant_id", "report_id", name="uq_dmarc_reports_tenant_id_report_id"),
    )

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ip", postgresql.INET(), nullable=False),
        _ts_column("first_seen"),
        _ts_column("last_seen"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_sources_tenant_id_tenants"),
        sa.UniqueConstraint("tenant_id", "ip", name="uq_sources_tenant_id_ip"),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("message", sa.Text(), nullable=False),
        _ts_column("created_at"),
        _ts_column("updated_at"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_alerts_tenant_id_tenants"),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], name="fk_alerts_domain_id_domains"),
    )

    _enable_tenant_rls("users")
    _enable_tenant_rls("domains")
    _enable_tenant_rls("dmarc_reports")
    _enable_tenant_rls("sources")
    _enable_tenant_rls("alerts")


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("sources")
    op.drop_table("dmarc_reports")
    op.drop_table("domains")
    op.drop_table("users")
    op.drop_table("tenants")
