"""The values the sources collected in every cycle, with their reference and collection instants, under RLS.

R1.3.8, ADR 0049.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "source_samples",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("flow_id", sa.Uuid, nullable=False),
        sa.Column("cycle_planned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("asset", sa.Text),
        sa.Column("reference_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_values", postgresql.JSONB, nullable=False),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
    )
    op.create_index("source_samples_of_cycle", "source_samples", ["flow_id", "cycle_planned_at"])
    op.execute("ALTER TABLE source_samples ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE source_samples FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY source_samples_of_tenant ON source_samples "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    # A collected value is a fact of a past cycle: it is only ever added (R1.3.8).
    op.execute(f"GRANT SELECT, INSERT ON source_samples TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("source_samples")
