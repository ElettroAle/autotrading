"""The reasons the history of the closed positions admits gain the liquidation, told as an event of its own.

R3.5.1, ADR eventi-notificabili-di-rischio-e-capitale.

Revision ID: 0038
Revises: 0037
"""

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

REASONS = (
    "'agent', 'manual', 'flow_stop', 'account_removal', 'outside_platform', 'stop_loss', 'take_profit', "
    "'protection_missing', 'cash_out', 'emergency'"
)
NEW_REASONS = "'liquidation'"


def upgrade() -> None:
    _reasons(f"{REASONS}, {NEW_REASONS}")


def downgrade() -> None:
    # A liquidation goes back to the reason it had before: a closing outside the platform.
    op.execute("UPDATE closed_positions SET reason = 'outside_platform' WHERE reason = 'liquidation'")
    _reasons(REASONS)


def _reasons(known: str) -> None:
    op.drop_constraint("closed_positions_reason_known", "closed_positions", type_="check")
    op.create_check_constraint("closed_positions_reason_known", "closed_positions", f"reason IN ({known})")
