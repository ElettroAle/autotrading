"""How often, in minutes, the periodic check reconciles an account while its flows hold open positions.

Empty unless the user sets it: the accounts that existed before read it empty and are reconciled every five minutes,
the default of the domain, with no data to migrate. The column belongs to the accounts, already under row level
security. Bug 778, ADR intervallo-di-riconciliazione-del-conto.

Revision ID: 0062
Revises: 0061
"""

import sqlalchemy as sa
from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("reconciliation_interval_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "reconciliation_interval_minutes")
