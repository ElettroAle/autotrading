"""What started every cycle: its schedule or the user, who asked for it now.

The cycles recorded before were all planned, and so is a row taken before its cycle runs until the cycle records
what started it. R6.5.2, ADR ciclo-su-richiesta-nel-worker.

Revision ID: 0035
Revises: 0033
"""

import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cycles", sa.Column("trigger", sa.Text, nullable=False, server_default="scheduled"))
    op.create_check_constraint("cycles_trigger_known", "cycles", "trigger IN ('scheduled', 'on_demand')")


def downgrade() -> None:
    op.drop_constraint("cycles_trigger_known", "cycles", type_="check")
    op.drop_column("cycles", "trigger")
