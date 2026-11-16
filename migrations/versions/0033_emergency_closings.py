"""The emergency closings of every tenant, under row level security: instant, scope and outcome of each flow; the
positions they close enter the history with their own reason.

A closing is history: it is written once, never changed nor deleted. The reasons the history admits gain the emergency
closing and the cash-out, whose reason the history did not admit yet (R3.4.1).
R3.2.3, ADR chiusura-di-emergenza-per-ambito.

Revision ID: 0033
Revises: 0032
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
REASONS = (
    "'agent', 'manual', 'flow_stop', 'account_removal', 'outside_platform', 'stop_loss', 'take_profit', "
    "'protection_missing'"
)
NEW_REASONS = "'cash_out', 'emergency'"


def upgrade() -> None:
    op.create_table(
        "emergency_closings",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope_kind", sa.Text, nullable=False),
        sa.Column("scope_id", sa.Uuid),
        sa.Column("outcome", postgresql.JSONB, nullable=False),
        sa.CheckConstraint("scope_kind IN ('flow', 'account', 'all')", name="emergency_closings_scope_kind"),
        sa.CheckConstraint("(scope_kind = 'all') = (scope_id IS NULL)", name="emergency_closings_scope_id"),
    )
    op.execute("ALTER TABLE emergency_closings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE emergency_closings FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY emergency_closings_of_tenant ON emergency_closings "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT ON emergency_closings TO {APPLICATION_ROLE}")
    _reasons(f"{REASONS}, {NEW_REASONS}")


def downgrade() -> None:
    _reasons(REASONS)
    op.drop_table("emergency_closings")


def _reasons(known: str) -> None:
    op.drop_constraint("closed_positions_reason_known", "closed_positions", type_="check")
    op.create_check_constraint("closed_positions_reason_known", "closed_positions", f"reason IN ({known})")
