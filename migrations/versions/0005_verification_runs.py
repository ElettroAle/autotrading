"""Runs of the procedure of verification with the outcome of each step, isolated per tenant by row level security.

R0.4.1, ADR 0024.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
# Without a tenant set for the transaction the setting is empty, the comparison is null and no row is visible.
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "verification_runs",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("environment", sa.Text, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("total_fee", sa.Numeric, nullable=False),
        sa.Column("realized_pnl", sa.Numeric, nullable=False),
        sa.Column("warning", sa.Text),
        # The steps are read together with their run and never queried alone (ADR 0024).
        sa.Column("steps", postgresql.JSONB, nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "tenant_id"],
            ["accounts.id", "accounts.tenant_id"],
            name="verification_runs_account_of_tenant",
        ),
    )
    op.execute("ALTER TABLE verification_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE verification_runs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY verification_runs_of_tenant ON verification_runs "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    # A run is a record of what the procedure did: the application adds runs, it never changes or deletes them.
    op.execute(f"GRANT SELECT, INSERT ON verification_runs TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("verification_runs")
