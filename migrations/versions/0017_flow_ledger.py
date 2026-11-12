"""The ledger of the executions of every account and the running totals of every flow, under row level security.

Bug 154, ADR 0063.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
LEDGER = ("account_fills", "account_funding")
STATE = ("account_fill_cursors", "flow_totals", "flow_position_totals")


def _account_of_tenant(name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], name=name)


def upgrade() -> None:
    op.create_table(
        "account_fills",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("fill_id", sa.Text, nullable=False),
        sa.Column("exchange_order_id", sa.Text, nullable=False),
        sa.Column("flow_id", sa.Uuid),
        sa.Column("order_id", sa.Uuid),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("platform_order", sa.Boolean, nullable=False),
        sa.Column("asset", sa.Text, nullable=False),
        sa.Column("size", sa.Numeric, nullable=False),
        sa.Column("price", sa.Numeric, nullable=False),
        sa.Column("fee", sa.Numeric, nullable=False),
        sa.Column("realized_pnl", sa.Numeric, nullable=False),
        sa.Column("start_position", sa.Numeric, nullable=False),
        sa.Column("liquidation", sa.Boolean, nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "account_id", "fill_id", "exchange_order_id", name="account_fills_once"),
        _account_of_tenant("account_fills_account_of_tenant"),
    )
    op.create_index("account_fills_of_flow", "account_fills", ["tenant_id", "flow_id", sa.text("executed_at DESC")])
    op.create_index(
        "account_fills_of_account", "account_fills", ["tenant_id", "account_id", sa.text("executed_at DESC")]
    )
    op.create_table(
        "account_funding",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("flow_id", sa.Uuid),
        sa.Column("asset", sa.Text, nullable=False),
        sa.Column("amount", sa.Numeric, nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "account_id", "asset", "paid_at", name="account_funding_once"),
        _account_of_tenant("account_funding_account_of_tenant"),
    )
    op.create_index("account_funding_of_flow", "account_funding", ["tenant_id", "flow_id", sa.text("paid_at DESC")])
    op.create_table(
        "account_fill_cursors",
        sa.Column("account_id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=False),
        _account_of_tenant("account_fill_cursors_account_of_tenant"),
    )
    op.create_table(
        "flow_totals",
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("realized_pnl", sa.Numeric, nullable=False),
        sa.Column("fees", sa.Numeric, nullable=False),
        sa.Column("funding", sa.Numeric, nullable=False),
    )
    op.create_table(
        "flow_position_totals",
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("asset", sa.Text, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("size", sa.Numeric, nullable=False),
    )
    for table in (*LEDGER, *STATE):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_of_tenant ON {table} "
            f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
        )
    for table in LEDGER:
        # The ledger is history: a row is added once, never changed or deleted.
        op.execute(f"GRANT SELECT, INSERT ON {table} TO {APPLICATION_ROLE}")
    for table in STATE:
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON {table} TO {APPLICATION_ROLE}")


def downgrade() -> None:
    for table in reversed((*LEDGER, *STATE)):
        op.drop_table(table)
