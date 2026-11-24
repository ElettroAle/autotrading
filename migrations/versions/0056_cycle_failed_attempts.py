"""Every cycle keeps the attempts of its steps that failed, retried in the same cycle or the one that stopped it.

The cycles recorded before keep it empty: nobody kept their attempts. Bug 718, ADR
errori-temporanei-ritentati-in-ogni-passo-del-ciclo.

Revision ID: 0056
Revises: 0055
"""

import sqlalchemy as sa
from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cycles", sa.Column("failed_attempts", sa.JSON))


def downgrade() -> None:
    op.drop_column("cycles", "failed_attempts")
