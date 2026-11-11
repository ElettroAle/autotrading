"""Keys of the AI model providers, sealed, at most one per provider and tenant, under row level security.

R1.4.1, ADR 0029.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "provider_keys",
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("provider", sa.Text, primary_key=True),
        sa.Column("key_version", sa.Integer, nullable=False),
        sa.Column("ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE provider_keys ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE provider_keys FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY provider_keys_of_tenant ON provider_keys "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON provider_keys TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("provider_keys")
