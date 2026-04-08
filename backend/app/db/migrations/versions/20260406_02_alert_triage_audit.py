"""Add alert triage columns and audit log table.

Revision ID: 20260406_02
Revises: 20260325_01
Create Date: 2026-04-06 09:00:00

"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260406_02"
down_revision = "20260325_01"
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
    op.add_column(
        "alerts",
        sa.Column("assignee", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "alert_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=320), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        _ts_column("created_at"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_alert_audit_logs_tenant_id_tenants",
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name="fk_alert_audit_logs_alert_id_alerts",
        ),
    )
    op.create_index(
        "ix_alert_audit_logs_tenant_alert_created_at",
        "alert_audit_logs",
        ["tenant_id", "alert_id", "created_at"],
    )
    _enable_tenant_rls("alert_audit_logs")


def downgrade() -> None:
    op.drop_index("ix_alert_audit_logs_tenant_alert_created_at", table_name="alert_audit_logs")
    op.drop_table("alert_audit_logs")
    op.drop_column("alerts", "escalation_level")
    op.drop_column("alerts", "assignee")
