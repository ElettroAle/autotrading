"""The last reading of each account and what no flow explains on it, under row level security.

R1.6.2, ADR 0045.

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "account_readings",
        sa.Column("account_id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_assets", postgresql.JSONB, nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "tenant_id"],
            ["accounts.id", "accounts.tenant_id"],
            name="account_readings_account_of_tenant",
        ),
    )
    op.create_table(
        "unattributable_items",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Uuid, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("reference", sa.Text, nullable=False),
        sa.Column("asset", sa.Text),
        sa.Column("amount", sa.Numeric, nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["account_id", "tenant_id"],
            ["accounts.id", "accounts.tenant_id"],
            name="unattributable_items_account_of_tenant",
        ),
    )
    # A case is recorded once while it lasts: a position closed and opened again is a new case (R1.6.2).
    op.create_index(
        "unattributable_items_open_case_unique",
        "unattributable_items",
        ["tenant_id", "account_id", "kind", "reference"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
    )
    for table in ("account_readings", "unattributable_items"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_of_tenant ON {table} "
            f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
        )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON account_readings TO {APPLICATION_ROLE}")
    # A recorded case is history: it is resolved, never deleted.
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON unattributable_items TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("unattributable_items")
    op.drop_table("account_readings")
