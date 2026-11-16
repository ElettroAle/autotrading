"""The exit plan in force of each open position of a flow, under row level security.

One row per flow and asset: an executed opening replaces it, the closing of the position removes it.
R3.1.1, ADR piano-di-uscita-nella-decisione-dell-agente.

Revision ID: 0028
Revises: 0027
"""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "flow_exit_plans",
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("asset", sa.Text, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("target_price", sa.Numeric),
        sa.Column("stop_price", sa.Numeric),
        sa.Column("invalidation", sa.Text),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
        sa.CheckConstraint("target_price IS NULL OR target_price > 0", name="flow_exit_plans_target_positive"),
        sa.CheckConstraint("stop_price IS NULL OR stop_price > 0", name="flow_exit_plans_stop_positive"),
    )
    op.execute("ALTER TABLE flow_exit_plans ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE flow_exit_plans FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY flow_exit_plans_of_tenant ON flow_exit_plans "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON flow_exit_plans TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("flow_exit_plans")
