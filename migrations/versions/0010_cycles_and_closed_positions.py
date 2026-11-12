"""The record of every cycle of a flow and the closed positions of the flows, under row level security.

R1.7.1, R1.7.2, R1.7.3, R1.4.6, ADR 0046, ADR 0047.

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
        "cycles",
        # The key is the planned instant of the flow: a second executor cannot take it again (ADR 0041).
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("planned_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("outcome", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("delay_seconds", sa.Integer),
        sa.Column("steps", postgresql.JSONB),
        sa.Column("absent_sources", postgresql.JSONB),
        sa.Column("failure", postgresql.JSONB),
        sa.Column("documents", postgresql.JSONB),
        sa.Column("input_tokens", sa.Integer),
        sa.Column("output_tokens", sa.Integer),
        sa.Column("cost_usd", sa.Numeric),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('completed', 'failed', 'skipped')", name="cycles_outcome_known"
        ),
    )
    op.create_table(
        "closed_positions",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("flow_id", sa.Uuid, nullable=False),
        sa.Column("asset", sa.Text, nullable=False),
        sa.Column("side", sa.Text, nullable=False),
        sa.Column("leverage", sa.Integer, nullable=False),
        sa.Column("margin", sa.Numeric, nullable=False),
        sa.Column("open_price", sa.Numeric, nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opening_cycle", sa.DateTime(timezone=True)),
        sa.Column("close_price", sa.Numeric, nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closing_cycle", sa.DateTime(timezone=True)),
        sa.Column("fees", sa.Numeric, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
        sa.CheckConstraint("side IN ('long', 'short')", name="closed_positions_side_known"),
        sa.CheckConstraint(
            "reason IN ('agent', 'manual', 'flow_stop', 'account_removal', 'outside_platform')",
            name="closed_positions_reason_known",
        ),
    )
    op.create_index("closed_positions_of_flow", "closed_positions", ["flow_id", "closed_at"])
    for table in ("cycles", "closed_positions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_of_tenant ON {table} "
            f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
        )
    # A recorded cycle is updated once, from taken to its outcome; nothing is ever deleted (R1.7.1).
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON cycles TO {APPLICATION_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON closed_positions TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("closed_positions")
    op.drop_table("cycles")
