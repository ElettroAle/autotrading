"""The bell of every tenant: each notification the platform generated for it, read or not, kept 90 days.

R6.2.1, ADR notifiche-nell-app-salvate-per-tenant. Under row level security; a notification older than 90 days is
deleted when the tenant receives another.

Revision ID: 0047
Revises: 0046
"""

import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
NEWEST = ("tenant_id", "notified_at DESC", "id DESC")


def upgrade() -> None:
    op.create_table(
        "inbox_notifications",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("icon", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("targets", sa.JSON, nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("inbox_notifications_newest", "inbox_notifications", [sa.text(column) for column in NEWEST])
    op.execute("ALTER TABLE inbox_notifications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE inbox_notifications FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY inbox_notifications_of_tenant ON inbox_notifications "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    # Notifications older than their retention are forgotten: the only rows the application deletes.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON inbox_notifications TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("inbox_notifications")
