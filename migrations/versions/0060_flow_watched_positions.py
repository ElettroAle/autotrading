"""The open positions of the flows whose stop follows the price, as the platform watches them, under row level
security.

One row per flow and asset: the opening it belongs to, the best price and the largest unrealized profit reached, and the
refusal of the exchange the next cycle tells. The closing of the position removes it; the configuration versions saved
before read the stop that follows the price as off, so no row and no new version is needed for them. R5.5.1, ADR
sorveglianza-del-prezzo-per-lo-stop-che-segue, ADR massimo-profitto-raggiunto-nello-stato-della-posizione.

Revision ID: 0060
Revises: 0059
"""

import sqlalchemy as sa
from alembic import op

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "flow_watched_positions",
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("asset", sa.Text, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("best_price", sa.Numeric, nullable=False),
        sa.Column("max_profit", sa.Numeric, nullable=False),
        sa.Column("refusal", sa.Text),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
        sa.CheckConstraint("best_price > 0", name="flow_watched_positions_best_price_positive"),
        sa.CheckConstraint("max_profit >= 0", name="flow_watched_positions_max_profit_not_negative"),
    )
    op.execute("ALTER TABLE flow_watched_positions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE flow_watched_positions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY flow_watched_positions_of_tenant ON flow_watched_positions "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON flow_watched_positions TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("flow_watched_positions")
