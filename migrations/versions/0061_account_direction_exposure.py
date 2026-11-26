"""The largest exposure the flows of an account may have together on one side, in percent of its balance read from the
exchange.

Empty unless the user sets it: the accounts that existed before read it empty and their flows open as before. The
column belongs to the accounts, already under row level security. R5.5.5, ADR
esposizione-massima-per-direzione-del-conto.

Revision ID: 0061
Revises: 0060
"""

import sqlalchemy as sa
from alembic import op

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("max_direction_exposure_percent", sa.Numeric(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "max_direction_exposure_percent")
