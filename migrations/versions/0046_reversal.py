"""The decisions of a cycle admit the reversal, and the history of the closed positions its own closing reason.

R1.4.10, ADR inversione-in-due-passi-nel-ciclo.

Revision ID: 0046
Revises: 0045
"""

from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None

ACTIONS = "'apri', 'chiudi', 'mantieni', 'aggiorna'"
NEW_ACTIONS = "'inverti'"
REASONS = (
    "'agent', 'manual', 'flow_stop', 'account_removal', 'outside_platform', 'stop_loss', 'take_profit', "
    "'protection_missing', 'cash_out', 'emergency', 'liquidation'"
)
NEW_REASONS = "'reversal'"


def upgrade() -> None:
    _actions(f"{ACTIONS}, {NEW_ACTIONS}")
    _reasons(f"{REASONS}, {NEW_REASONS}")


def downgrade() -> None:
    # Before the reversal a closing it asked was a closing decided by the agent, and its decision a closing.
    op.execute("UPDATE closed_positions SET reason = 'agent' WHERE reason = 'reversal'")
    op.execute("UPDATE cycle_decisions SET action = 'chiudi' WHERE action = 'inverti'")
    _reasons(REASONS)
    _actions(ACTIONS)


def _actions(known: str) -> None:
    op.drop_constraint("cycle_decisions_action_known", "cycle_decisions", type_="check")
    op.create_check_constraint("cycle_decisions_action_known", "cycle_decisions", f"action IN ({known})")


def _reasons(known: str) -> None:
    op.drop_constraint("closed_positions_reason_known", "closed_positions", type_="check")
    op.create_check_constraint("closed_positions_reason_known", "closed_positions", f"reason IN ({known})")
