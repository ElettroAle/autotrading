"""The accounts of the simulated exchange, each of one tenant under row level security: the virtual balance and the
leverage set on each asset, the open positions, the protections waiting for their price, and the history of the
executions and of the movements of the balance (R6.3.2, ADR exchange-simulato-con-porte-di-lettura-e-scrittura).

The account of the simulated exchange opens before the account of the platform is saved, which reads its balance
first: it refers to no row of the accounts table.

Revision ID: 0057
Revises: 0056
"""

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
ACCOUNTS = "simulated_accounts.account_id"
STATE_TABLES = ("simulated_accounts", "simulated_positions", "simulated_protections")
HISTORY_TABLES = ("simulated_fills", "simulated_movements")


def upgrade() -> None:
    op.create_table(
        "simulated_accounts",
        sa.Column("account_id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("balance", sa.Numeric, nullable=False),
        sa.Column("leverages", sa.JSON, nullable=False),
    )
    op.create_table(
        "simulated_positions",
        sa.Column("account_id", sa.Uuid, sa.ForeignKey(ACCOUNTS), primary_key=True),
        sa.Column("coin", sa.Text, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("size", sa.Numeric, nullable=False),
        sa.Column("leverage", sa.Integer, nullable=False),
        sa.Column("entry_price", sa.Numeric, nullable=False),
        sa.Column("margin", sa.Numeric, nullable=False),
        sa.Column("maintenance_rate", sa.Numeric, nullable=False),
        sa.Column("mark_price", sa.Numeric),
    )
    op.create_table(
        "simulated_protections",
        sa.Column("order_id", sa.Text, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, sa.ForeignKey(ACCOUNTS), nullable=False),
        sa.Column("coin", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("closing_direction", sa.Text, nullable=False),
        sa.Column("trigger_price", sa.Numeric, nullable=False),
        sa.Column("client_order_id", sa.Uuid, nullable=False, unique=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "simulated_fills",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, sa.ForeignKey(ACCOUNTS), nullable=False),
        sa.Column("exchange_order_id", sa.Text, nullable=False),
        sa.Column("client_order_id", sa.Uuid),
        sa.Column("coin", sa.Text, nullable=False),
        sa.Column("is_buy", sa.Boolean, nullable=False),
        sa.Column("size", sa.Numeric, nullable=False),
        sa.Column("price", sa.Numeric, nullable=False),
        sa.Column("fee", sa.Numeric, nullable=False),
        sa.Column("realized_pnl", sa.Numeric, nullable=False),
        sa.Column("start_position", sa.Numeric, nullable=False),
        sa.Column("liquidation", sa.Boolean, nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("simulated_fills_of_account", "simulated_fills", ["tenant_id", "account_id", "executed_at"])
    op.create_table(
        "simulated_movements",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, sa.ForeignKey(ACCOUNTS), nullable=False),
        sa.Column("amount", sa.Numeric, nullable=False),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=False),
    )
    for table in (*STATE_TABLES, *HISTORY_TABLES):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_of_tenant ON {table} "
            f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
        )
    for table in STATE_TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APPLICATION_ROLE}")
    # The history is written once, never changed or deleted.
    for table in HISTORY_TABLES:
        op.execute(f"GRANT SELECT, INSERT ON {table} TO {APPLICATION_ROLE}")


def downgrade() -> None:
    for table in reversed((*STATE_TABLES, *HISTORY_TABLES)):
        op.drop_table(table)
