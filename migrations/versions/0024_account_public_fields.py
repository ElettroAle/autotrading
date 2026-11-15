"""The public fields of the credentials of an account, in clear next to the digest of its exchange account.

The fields the adapter of the exchange declares public (ADR 0158), such as the account address: a replacement of the
credentials asks only the secret ones, and the account shows them. Empty for the accounts registered before: they get
them at their next replacement. Bug 401, ADR campi-pubblici-del-conto-conservati-in-chiaro.

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("exchange_account_public_fields", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "exchange_account_public_fields")
