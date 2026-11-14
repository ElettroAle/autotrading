"""Flows in draft: the strategy alone, without account until the user assigns one.

The account becomes optional only for a draft, or a draft archived without ever starting: every other flow keeps it.
R2.4.1, ADR 0124.

Revision ID: 0021
Revises: 0020
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("flows_status_known", "flows", type_="check")
    op.create_check_constraint(
        "flows_status_known", "flows", "status IN ('draft', 'stopped', 'active', 'paused', 'archived')"
    )
    op.alter_column("flows", "account_id", nullable=True)
    op.create_check_constraint(
        "flows_account_outside_draft", "flows", "account_id IS NOT NULL OR status IN ('draft', 'archived')"
    )


def downgrade() -> None:
    # Drafts must be archived or removed first: a flow without account has no place in the previous schema.
    op.drop_constraint("flows_account_outside_draft", "flows", type_="check")
    op.alter_column("flows", "account_id", nullable=False)
    op.drop_constraint("flows_status_known", "flows", type_="check")
    op.create_check_constraint("flows_status_known", "flows", "status IN ('stopped', 'active', 'paused', 'archived')")
