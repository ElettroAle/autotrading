"""The credentials of the adapters of the sources of each tenant: the public values in clear, the secret ones sealed.

R4.1.2, ADR credenziali-degli-adapter-delle-fonti. One row per tenant and adapter, under row level security; the expiry
the user gives and the instant the provider refused them beside. The thresholds told for an expiry also name the
credentials of an adapter (R6.2.2).

Revision ID: 0051
Revises: 0050
"""

import sqlalchemy as sa
from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "source_credentials",
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("adapter", sa.Text, primary_key=True),
        sa.Column("public_values", sa.JSON, nullable=False),
        sa.Column("key_version", sa.Integer, nullable=False),
        sa.Column("ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("expires_on", sa.Date),
        sa.Column("expiry_source", sa.Text),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("expiry_source IN ('read', 'entered')", name="source_credentials_expiry_source_known"),
        sa.CheckConstraint("(expires_on IS NULL) = (expiry_source IS NULL)", name="source_credentials_expiry_complete"),
    )
    op.execute("ALTER TABLE source_credentials ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE source_credentials FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY source_credentials_of_tenant ON source_credentials "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON source_credentials TO {APPLICATION_ROLE}")
    op.drop_constraint("key_expiry_notices_kind_known", "key_expiry_notices", type_="check")
    op.create_check_constraint(
        "key_expiry_notices_kind_known", "key_expiry_notices", "key_kind IN ('account', 'provider', 'source')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM key_expiry_notices WHERE key_kind = 'source'")
    op.drop_constraint("key_expiry_notices_kind_known", "key_expiry_notices", type_="check")
    op.create_check_constraint(
        "key_expiry_notices_kind_known", "key_expiry_notices", "key_kind IN ('account', 'provider')"
    )
    op.drop_table("source_credentials")
