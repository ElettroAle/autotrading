"""The alerts of every tenant: what asks the user to act, from any source, open until its cause goes.

R6.2.3, ADR avvisi-nel-contesto-delle-notifiche. One alert open per cause, under row level security; an alert resolved
more than 90 days ago is deleted when the tenant opens another.

Revision ID: 0044
Revises: 0043
"""

import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
NEWEST = ("tenant_id", "opened_at DESC", "id DESC")


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("resource_kind", sa.Text, nullable=False),
        sa.Column("resource_id", sa.Uuid, nullable=False),
        sa.Column("resource_name", sa.Text, nullable=False),
        sa.Column("detail", sa.Text, nullable=False),
        sa.Column("cause_key", sa.Text, nullable=False),
        sa.Column("readings", sa.JSON, nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    # Two cycles of the same account may open the same alert together: the database keeps one open per cause.
    op.create_index(
        "alerts_open_cause_unique",
        "alerts",
        ["tenant_id", "cause_key"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
    )
    op.create_index("alerts_newest", "alerts", [sa.text(column) for column in NEWEST])
    op.execute("ALTER TABLE alerts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alerts FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY alerts_of_tenant ON alerts "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    # Resolved alerts are forgotten after their retention: the only rows the application deletes.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON alerts TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("alerts")
