"""A removed account keeps its row for the history and loses its credentials; its name is free again.

R0.2.5, ADR 0025.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

NAME_UNIQUE_IN_TENANT = "accounts_name_unique_in_tenant"
CREDENTIALS_UNLESS_REMOVED = "accounts_credentials_unless_removed"


def upgrade() -> None:
    op.add_column("accounts", sa.Column("removed_at", sa.DateTime(timezone=True)))
    op.alter_column("accounts", "credentials_key_version", nullable=True)
    op.alter_column("accounts", "credentials_ciphertext", nullable=True)
    # An account in use always has its credentials; a removed one never keeps them.
    op.create_check_constraint(
        CREDENTIALS_UNLESS_REMOVED,
        "accounts",
        "(removed_at IS NULL AND credentials_key_version IS NOT NULL AND credentials_ciphertext IS NOT NULL) "
        "OR (removed_at IS NOT NULL AND credentials_key_version IS NULL AND credentials_ciphertext IS NULL)",
    )
    # The name is unique among the accounts in use: a removed account frees it.
    op.drop_constraint(NAME_UNIQUE_IN_TENANT, "accounts")
    op.create_index(
        NAME_UNIQUE_IN_TENANT,
        "accounts",
        ["tenant_id", "name"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(NAME_UNIQUE_IN_TENANT, "accounts")
    op.execute("DELETE FROM accounts WHERE removed_at IS NOT NULL")
    op.create_unique_constraint(NAME_UNIQUE_IN_TENANT, "accounts", ["tenant_id", "name"])
    op.drop_constraint(CREDENTIALS_UNLESS_REMOVED, "accounts")
    op.alter_column("accounts", "credentials_ciphertext", nullable=False)
    op.alter_column("accounts", "credentials_key_version", nullable=False)
    op.drop_column("accounts", "removed_at")
