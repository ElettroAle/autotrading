"""The history of the capital allocated to every flow, under row level security.

R1.1.7, ADR 0053.

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "flow_capital_changes",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("flow_id", sa.Uuid, nullable=False),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        # Amounts as exact numbers: the history shows what the user wrote, never a rounded value.
        sa.Column("previous_capital", sa.Numeric, nullable=False),
        sa.Column("new_capital", sa.Numeric, nullable=False),
        sa.Column("user_id", sa.Text, nullable=False),
        # The version the change created: the capital each cycle used is in the version it ran on (R1.1.3).
        sa.Column("version", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
        sa.ForeignKeyConstraint(["flow_id", "version"], ["flow_versions.flow_id", "flow_versions.version"]),
    )
    op.create_index("flow_capital_changes_of_flow", "flow_capital_changes", ["flow_id", "changed_at"])
    op.execute("ALTER TABLE flow_capital_changes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE flow_capital_changes FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY flow_capital_changes_of_tenant ON flow_capital_changes "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    # A recorded change is never changed nor deleted: the history stays what happened (R1.1.7).
    op.execute(f"GRANT SELECT, INSERT ON flow_capital_changes TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("flow_capital_changes")
