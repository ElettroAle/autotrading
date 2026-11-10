"""Orders sent to the exchange with the outcome it gave them, isolated per tenant by row level security.

R0.3.1, R0.3.3, R0.3.4, ADR 0022.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
ACCOUNT_OF_TENANT = "accounts_id_tenant_unique"
# Without a tenant set for the transaction the setting is empty, the comparison is null and no row is visible.
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_unique_constraint(ACCOUNT_OF_TENANT, "accounts", ["id", "tenant_id"])
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("origin", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text),
        sa.Column("coin", sa.Text, nullable=False),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("reduce_only", sa.Boolean, nullable=False),
        sa.Column("leverage", sa.Integer, nullable=False),
        sa.Column("requested_size", sa.Numeric, nullable=False),
        sa.Column("slippage", sa.Numeric, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("filled_size", sa.Numeric),
        sa.Column("average_price", sa.Numeric),
        sa.Column("fee", sa.Numeric),
        sa.Column("realized_pnl", sa.Numeric),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("rejection_reason", sa.Text),
        sa.Column("exchange_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # The account of an order belongs to the tenant of the order: row level security alone would not say it,
        # because a foreign key is checked without it.
        sa.ForeignKeyConstraint(
            ["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], name="orders_account_of_tenant"
        ),
    )
    op.execute("ALTER TABLE orders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE orders FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY orders_of_tenant ON orders "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    # An order is a record of what the exchange did: the application adds orders, it never changes or deletes them.
    op.execute(f"GRANT SELECT, INSERT ON orders TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_constraint(ACCOUNT_OF_TENANT, "accounts")
