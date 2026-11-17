"""The mail server of each tenant, with its password sealed, under row level security.

R3.5.5, ADR server-di-posta-per-tenant.

Revision ID: 0040
Revises: 0039
"""

import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "notification_mail_servers",
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("host", sa.Text, nullable=False),
        sa.Column("port", sa.Integer, nullable=False),
        sa.Column("security", sa.Text, nullable=False),
        sa.Column("username", sa.Text, nullable=False),
        sa.Column("sender", sa.Text, nullable=False),
        sa.Column("sealed_password", sa.LargeBinary, nullable=False),
        sa.Column("key_version", sa.Integer, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("port BETWEEN 1 AND 65535", name="notification_mail_servers_port_in_range"),
        sa.CheckConstraint("security IN ('STARTTLS', 'TLS')", name="notification_mail_servers_security_known"),
    )
    op.execute("ALTER TABLE notification_mail_servers ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notification_mail_servers FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY notification_mail_servers_of_tenant ON notification_mail_servers "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON notification_mail_servers TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("notification_mail_servers")
