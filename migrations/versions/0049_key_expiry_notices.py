"""The thresholds told for each expiry of a key: 30, 7 and 1 days before and the day itself, once each.

R6.2.2, ADR controllo-giornaliero-delle-scadenze. Under row level security; the primary key holds the key, the date it
told and the threshold, so a new date of the key is told again and two checks together tell a threshold once.

Revision ID: 0049
Revises: 0048
"""

import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "key_expiry_notices",
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("key_kind", sa.Text, primary_key=True),
        sa.Column("key_id", sa.Uuid, primary_key=True),
        sa.Column("expires_on", sa.Date, primary_key=True),
        sa.Column("threshold", sa.Integer, primary_key=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("key_kind IN ('account', 'provider')", name="key_expiry_notices_kind_known"),
    )
    op.execute("ALTER TABLE key_expiry_notices ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE key_expiry_notices FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY key_expiry_notices_of_tenant ON key_expiry_notices "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT ON key_expiry_notices TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("key_expiry_notices")
