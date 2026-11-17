"""Every cycle says whether it called the model, also when the call failed before its usage was known.

The cycles recorded before had a call exactly when they kept its tokens. R1.4.6, Bug 541,
ADR costo-della-decisione-fallita-nel-registro-del-ciclo.

Revision ID: 0034
Revises: 0033
"""

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cycles", sa.Column("model_called", sa.Boolean, nullable=False, server_default=sa.text("false")))
    # Row level security forced on the table hides every row from the owner too, without a tenant: the cycles of
    # every tenant change only while it is lifted, inside the transaction of the migration.
    op.execute("ALTER TABLE cycles NO FORCE ROW LEVEL SECURITY")
    op.execute("UPDATE cycles SET model_called = true WHERE input_tokens IS NOT NULL")
    op.execute("ALTER TABLE cycles FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_column("cycles", "model_called")
