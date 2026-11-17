"""The channel of every type of event of each tenant and the exceptions of its flows, under row level security.

R3.5.3, ADR canali-delle-notifiche-per-tipo-di-evento.

Revision ID: 0036
Revises: 0035
"""

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
# The types of event are not listed: a new one is chosen without a migration (ADR
# eventi-notificabili-di-rischio-e-capitale).
CHANNELS = "channel IN ('telegram', 'email', 'both', 'none')"


def upgrade() -> None:
    op.create_table(
        "notification_channels",
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("event", sa.Text, primary_key=True),
        sa.Column("channel", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(CHANNELS, name="notification_channels_channel_known"),
    )
    op.create_table(
        "notification_channel_exceptions",
        sa.Column("tenant_id", sa.Uuid, primary_key=True),
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("event", sa.Text, primary_key=True),
        sa.Column("channel", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"], name="notification_channel_exceptions_flow"
        ),
        sa.CheckConstraint(CHANNELS, name="notification_channel_exceptions_channel_known"),
    )
    for table in ("notification_channels", "notification_channel_exceptions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_of_tenant ON {table} "
            f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("notification_channel_exceptions")
    op.drop_table("notification_channels")
