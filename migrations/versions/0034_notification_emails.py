"""The address of the notifications by email of each tenant, under row level security.

R3.5.2, ADR canale-email-delle-notifiche-con-smtp.

Revision ID: 0034
Revises: 0033
"""

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "notification_emails",
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE notification_emails ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notification_emails FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY notification_emails_of_tenant ON notification_emails "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON notification_emails TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("notification_emails")
