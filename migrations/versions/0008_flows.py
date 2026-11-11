"""Trading flows and their numbered configuration versions, under row level security.

R1.1.1, ADR 0031.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "flows",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # The account of a flow belongs to the same tenant, whatever the row level security lets through.
        sa.ForeignKeyConstraint(
            ["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], name="flows_account_of_tenant"
        ),
        sa.UniqueConstraint("id", "tenant_id", name="flows_id_tenant_unique"),
        sa.CheckConstraint("status IN ('stopped', 'active', 'paused', 'archived')", name="flows_status_known"),
    )
    op.create_index(
        "flows_name_unique_in_tenant",
        "flows",
        ["tenant_id", "name"],
        unique=True,
        postgresql_where=sa.text("status <> 'archived'"),
    )
    op.create_table(
        "flow_versions",
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("version", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("configuration", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
    )
    for table in ("flows", "flow_versions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_of_tenant ON {table} "
            f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
        )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON flows TO {APPLICATION_ROLE}")
    # A version is never changed nor deleted: every cycle can be rebuilt with the one it used (R1.1.3).
    op.execute(f"GRANT SELECT, INSERT ON flow_versions TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("flow_versions")
    op.drop_table("flows")
