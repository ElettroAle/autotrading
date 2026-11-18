"""The movement no flow explains is no longer a type of event told to the user: the channels chosen for it go.

Bug 596, ADR variazioni-sotto-soglia-senza-notifica. A change of the balance within the threshold is only recorded, so
the choices of every tenant and the exceptions of their flows for that type would name an event that is gone.

Revision ID: 0042
Revises: 0041
"""

import sqlalchemy as sa
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

TABLES = ("notification_channels", "notification_channel_exceptions")
REMOVED_EVENT = "unattributable_movement"


def upgrade() -> None:
    for table in TABLES:
        # Row level security forced on the table hides every row from the owner too, without a tenant: the choices of
        # every tenant go only while it is lifted, inside the transaction of the migration.
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        choices = sa.table(table, sa.column("event", sa.Text))
        op.execute(choices.delete().where(choices.c.event == REMOVED_EVENT))
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # The choices removed are not known any more: a tenant who has the type again chooses its channels again.
    pass
