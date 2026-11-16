"""The profits a flow had cashed out at each cycle, which its equity leaves out as the value of the flow does.

The ranking chains the return across the changes of the capital on these equities. The cycles recorded before had
nothing cashed out to leave out. R3.4.3, ADR rendimento-composto-tra-le-variazioni-di-capitale.

Revision ID: 0026
Revises: 0025
"""

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("equity_snapshots", sa.Column("cashed_profit", sa.Numeric, nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("equity_snapshots", "cashed_profit")
