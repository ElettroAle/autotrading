"""The deposits, withdrawals and transfers of every account in the ledger, under row level security.

Bug 635, ADR movimenti-del-conto-nel-registro-con-cursore. Read with the executions from the cursor of the account, they
are written once and read by instant for the rows after the previous reading that explain its balance.

Revision ID: 0054
Revises: 0053
"""

import sqlalchemy as sa
from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
TABLE = "account_movements"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("movement_id", sa.Text, nullable=False),
        sa.Column("amount", sa.Numeric, nullable=False),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "account_id", "movement_id", "moved_at", name="account_movements_once"),
        sa.ForeignKeyConstraint(
            ["account_id", "tenant_id"],
            ["accounts.id", "accounts.tenant_id"],
            name="account_movements_account_of_tenant",
        ),
    )
    op.create_index(
        "account_movements_of_account", "account_movements", ["tenant_id", "account_id", sa.text("moved_at DESC")]
    )
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {TABLE}_of_tenant ON {TABLE} "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    # The ledger is history: a row is added once, never changed or deleted.
    op.execute(f"GRANT SELECT, INSERT ON {TABLE} TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table(TABLE)
