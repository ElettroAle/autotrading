"""Trading accounts with sealed credentials, isolated per tenant by row level security (R0.2.1, R0.1.3).

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
# Without a tenant set for the transaction the setting is empty, the comparison is null and no row is visible.
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("exchange", sa.Text, nullable=False),
        sa.Column("credentials_key_version", sa.Integer, nullable=False),
        sa.Column("credentials_ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="accounts_name_unique_in_tenant"),
    )
    op.execute("ALTER TABLE accounts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE accounts FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY accounts_of_tenant ON accounts "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON accounts TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("accounts")
