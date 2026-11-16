"""The balance of the accounts compared at every reconciliation, and the alarms beyond the threshold of each account.

The threshold of an existing account is the default, 1%. A reading saved before has no reference: the next
reconciliation takes it from the exchange. At most one alarm open per account, under row level security.
R3.3.1, ADR allarme-di-riconciliazione-sul-saldo-del-conto.

Revision ID: 0025
Revises: 0024
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
READING_BALANCES = ("reference_balance", "expected_balance", "read_balance")


def upgrade() -> None:
    op.add_column(
        "accounts", sa.Column("deviation_threshold", sa.Numeric(), nullable=False, server_default=sa.text("1"))
    )
    for column in READING_BALANCES:
        op.add_column("account_readings", sa.Column(column, sa.Numeric(), nullable=True))
    op.create_table(
        "reconciliation_alarms",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("expected_balance", sa.Numeric, nullable=False),
        sa.Column("read_balance", sa.Numeric, nullable=False),
        sa.Column("deviation_percent", sa.Numeric, nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["account_id", "tenant_id"],
            ["accounts.id", "accounts.tenant_id"],
            name="reconciliation_alarms_account_of_tenant",
        ),
    )
    # Two cycles of the same account may compare together: the database keeps one alarm open (R3.3.1).
    op.create_index(
        "reconciliation_alarms_open_unique",
        "reconciliation_alarms",
        ["tenant_id", "account_id"],
        unique=True,
        postgresql_where=sa.text("confirmed_at IS NULL"),
    )
    op.execute("ALTER TABLE reconciliation_alarms ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE reconciliation_alarms FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY reconciliation_alarms_of_tenant ON reconciliation_alarms "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    # An alarm is history: it is confirmed, never deleted.
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON reconciliation_alarms TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("reconciliation_alarms")
    for column in reversed(READING_BALANCES):
        op.drop_column("account_readings", column)
    op.drop_column("accounts", "deviation_threshold")
