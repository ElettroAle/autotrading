"""The expiry of every key: the day the credentials of an account or the key of a provider stop working, and who
gave it.

R6.2.2, ADR scadenza-delle-chiavi-letta-o-indicata. Both empty while the expiry is unknown; the date is read by the
adapter of the exchange or given by the user.

Revision ID: 0048
Revises: 0047
"""

import sqlalchemy as sa
from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None

TABLES = ("accounts", "provider_keys")
SOURCES = "expiry_source IN ('read', 'entered')"
BOTH_OR_NEITHER = "(expires_on IS NULL) = (expiry_source IS NULL)"


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("expires_on", sa.Date))
        op.add_column(table, sa.Column("expiry_source", sa.Text))
        op.create_check_constraint(f"{table}_expiry_source_known", table, SOURCES)
        op.create_check_constraint(f"{table}_expiry_complete", table, BOTH_OR_NEITHER)


def downgrade() -> None:
    for table in TABLES:
        op.drop_constraint(f"{table}_expiry_complete", table)
        op.drop_constraint(f"{table}_expiry_source_known", table)
        op.drop_column(table, "expiry_source")
        op.drop_column(table, "expires_on")
