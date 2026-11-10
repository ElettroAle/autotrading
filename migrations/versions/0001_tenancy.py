"""Tenants and memberships (R0.1.2).

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "memberships",
        sa.Column("user_id", sa.Text, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False, unique=True),
    )
    op.execute(f"GRANT SELECT, INSERT ON tenants, memberships TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("tenants")
