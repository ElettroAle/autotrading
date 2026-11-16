"""The stop loss and take profit orders the platform placed on the exchange for the positions of the flows, under row
level security, and the closings they make in the history of the flows.

A protection stays recorded once removed: its execution, read later from the exchange, still belongs to its flow.
R3.1.2, ADR ordini-di-protezione-sull-exchange, ADR chiusure-per-protezione-nello-storico.

Revision ID: 0029
Revises: 0028
"""

import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
REASONS = "'agent', 'manual', 'flow_stop', 'account_removal', 'outside_platform'"
PROTECTION_REASONS = "'stop_loss', 'take_profit', 'protection_missing'"


def upgrade() -> None:
    op.create_table(
        "flow_protections",
        sa.Column("client_order_id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("flow_id", sa.Uuid, nullable=False),
        sa.Column("asset", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("trigger_price", sa.Numeric, nullable=False),
        sa.Column("exchange_order_id", sa.Text, nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"]),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
        sa.CheckConstraint("kind IN ('stop_loss', 'take_profit')", name="flow_protections_kind_known"),
        sa.CheckConstraint("trigger_price > 0", name="flow_protections_trigger_positive"),
    )
    op.create_index("flow_protections_of_position", "flow_protections", ["account_id", "asset"])
    op.execute("ALTER TABLE flow_protections ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE flow_protections FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY flow_protections_of_tenant ON flow_protections "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON flow_protections TO {APPLICATION_ROLE}")
    _reasons(f"{REASONS}, {PROTECTION_REASONS}")


def downgrade() -> None:
    _reasons(REASONS)
    op.drop_table("flow_protections")


def _reasons(known: str) -> None:
    op.drop_constraint("closed_positions_reason_known", "closed_positions", type_="check")
    op.create_check_constraint("closed_positions_reason_known", "closed_positions", f"reason IN ({known})")
