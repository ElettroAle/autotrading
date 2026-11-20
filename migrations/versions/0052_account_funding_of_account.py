"""The funding of an account by instant, for the rows after the previous reading that explain its balance.

Bug 633, ADR saldo-atteso-dalle-righe-del-registro-dopo-la-lettura-precedente. The executions of an account by instant
have their index since revision 0017 (account_fills_of_account), which serves the same reading.

Revision ID: 0052
Revises: 0051
"""

import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "account_funding_of_account", "account_funding", ["tenant_id", "account_id", sa.text("paid_at DESC")]
    )


def downgrade() -> None:
    op.drop_index("account_funding_of_account", table_name="account_funding")
