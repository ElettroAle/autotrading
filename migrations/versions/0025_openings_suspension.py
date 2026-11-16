"""The openings of every flow suspended for maximum loss: the threshold passed, when, and their last resume.

Beside the flow, under its row level security; empty for every flow until a threshold is passed. R3.2.2, ADR
perdita-massima-sui-valori-di-equity-registrati.

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
    op.add_column("flows", sa.Column("openings_suspension_reason", sa.Text(), nullable=True))
    op.add_column("flows", sa.Column("openings_suspended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("flows", sa.Column("openings_resumed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("flows", "openings_resumed_at")
    op.drop_column("flows", "openings_suspended_at")
    op.drop_column("flows", "openings_suspension_reason")
