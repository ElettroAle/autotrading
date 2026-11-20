"""The forecasts still awaiting their actual price, read by the worker every few seconds without reading them all.

Bug 635, ADR indice-delle-previsioni-in-attesa-e-patrimonio-con-limite-superiore.

Revision ID: 0053
Revises: 0052
"""

import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "forecasts_awaiting_actual",
        "forecasts",
        ["tenant_id", "made_at"],
        postgresql_where=sa.text("actual_price IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("forecasts_awaiting_actual", table_name="forecasts")
