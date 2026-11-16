"""Why the capital of a flow changed, how much money moved, the value of the flow before and the profit cashed out.

A cash-out records its change on the version in force when it keeps the capital; the profits cashed out leave the
money of the flow for the free capital of the account. The changes recorded before have the reason their sign gives,
the difference as amount and no value before. R3.4.1, ADR incasso-dei-profitti, ADR
capitale-libero-al-netto-del-valore-dei-flussi.

Revision ID: 0025
Revises: 0024
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("flow_capital_changes", sa.Column("reason", sa.Text, nullable=True))
    op.add_column("flow_capital_changes", sa.Column("amount", sa.Numeric, nullable=True))
    op.add_column("flow_capital_changes", sa.Column("value_before", sa.Numeric, nullable=True))
    op.add_column("flow_capital_changes", sa.Column("cashed_profit", sa.Numeric, nullable=False, server_default="0"))
    op.execute(
        "UPDATE flow_capital_changes SET "
        "reason = CASE WHEN new_capital > previous_capital THEN 'aumento' ELSE 'riduzione' END, "
        "amount = abs(new_capital - previous_capital)"
    )
    op.alter_column("flow_capital_changes", "reason", nullable=False)
    op.alter_column("flow_capital_changes", "amount", nullable=False)
    op.create_check_constraint(
        "flow_capital_changes_reason", "flow_capital_changes", "reason IN ('aumento', 'riduzione', 'incasso')"
    )


def downgrade() -> None:
    op.drop_constraint("flow_capital_changes_reason", "flow_capital_changes")
    op.drop_column("flow_capital_changes", "cashed_profit")
    op.drop_column("flow_capital_changes", "value_before")
    op.drop_column("flow_capital_changes", "amount")
    op.drop_column("flow_capital_changes", "reason")
