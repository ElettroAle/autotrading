"""The channels of a type of event as a set: an array of channel names, empty for none, in place of the combinations.

Bug 578, ADR canali-delle-notifiche-come-insieme. The choices are kept: telegram, email, both and none become the arrays
of the channels they reached.

Revision ID: 0041
Revises: 0040
"""

import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None

TABLES = ("notification_channels", "notification_channel_exceptions")
KNOWN_CHANNELS = "ARRAY['telegram', 'email']::text[]"
CHANNELS_OF_CHOICE = (
    "CASE channel"
    " WHEN 'telegram' THEN ARRAY['telegram']"
    " WHEN 'email' THEN ARRAY['email']"
    " WHEN 'both' THEN ARRAY['telegram', 'email']"
    " ELSE ARRAY[]::text[] END"
)
# Back to the combinations: every set of the two channels has its name among them.
CHOICE_OF_CHANNELS = (
    "CASE"
    " WHEN channels = ARRAY[]::text[] THEN 'none'"
    " WHEN channels @> ARRAY['telegram', 'email'] THEN 'both'"
    " WHEN channels = ARRAY['telegram'] THEN 'telegram'"
    " ELSE 'email' END"
)
COMBINATIONS = "channel IN ('telegram', 'email', 'both', 'none')"


def _choices(table: str) -> sa.TableClause:
    return sa.table(table, sa.column("channel", sa.Text), sa.column("channels", sa.ARRAY(sa.Text)))


def _converted(table: str, conversion: sa.Update) -> None:
    # Row level security forced on the table hides every row from the owner too, without a tenant: the choices of
    # every tenant change only while it is lifted, inside the transaction of the migration.
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(conversion)
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN channels text[]")
        _converted(table, _choices(table).update().values(channels=sa.text(CHANNELS_OF_CHOICE)))
        op.execute(f"ALTER TABLE {table} ALTER COLUMN channels SET NOT NULL")
        op.execute(f"ALTER TABLE {table} DROP COLUMN channel")
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {table}_channels_known CHECK (channels <@ {KNOWN_CHANNELS})")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN channel text")
        _converted(table, _choices(table).update().values(channel=sa.text(CHOICE_OF_CHANNELS)))
        op.execute(f"ALTER TABLE {table} ALTER COLUMN channel SET NOT NULL")
        op.execute(f"ALTER TABLE {table} DROP COLUMN channels")
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {table}_channel_known CHECK ({COMBINATIONS})")
