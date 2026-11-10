"""The exchange account an account operates, kept as a digest of its address (R0.2.4, ADR 0019).

No account can exist before this revision outside a test database: the API refuses every request while
authentication is not configured, so the column is required from the start.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("exchange_account_fingerprint", sa.Text, nullable=False))


def downgrade() -> None:
    op.drop_column("accounts", "exchange_account_fingerprint")
