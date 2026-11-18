"""Every cycle keeps how many calls the decision of the agent tried, beside their cost.

The cycles recorded before keep it empty: nobody counted their attempts. R1.4.9,
ADR tentativi-del-modello-registrati-nel-ciclo.

Revision ID: 0045
Revises: 0044
"""

import sqlalchemy as sa
from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cycles", sa.Column("model_attempts", sa.Integer))


def downgrade() -> None:
    op.drop_column("cycles", "model_attempts")
