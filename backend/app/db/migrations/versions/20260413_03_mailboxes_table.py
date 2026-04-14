"""Add persistent mailboxes table.

Revision ID: 20260413_03
Revises: 20260406_02
Create Date: 2026-04-13 12:30:00

"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260413_03"
down_revision = "20260406_02"
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
        "mailboxes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("username", sa.String(length=320), nullable=False),
        sa.Column("password", sa.String(length=256), nullable=False),
        sa.Column("server", sa.String(length=255), nullable=False),
        sa.Column("mailbox", sa.String(length=255), nullable=False, server_default="INBOX"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        _ts_column("created_at"),
        _ts_column("updated_at"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_mailboxes_tenant_id_tenants",
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_mailboxes_tenant_id_name"),
    )

    op.create_index(
        "ix_mailboxes_tenant_enabled",
        "mailboxes",
        ["tenant_id", "enabled"],
    )

    _enable_tenant_rls("mailboxes")


def downgrade() -> None:
    op.drop_index("ix_mailboxes_tenant_enabled", table_name="mailboxes")
    op.drop_table("mailboxes")