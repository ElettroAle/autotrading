"""The motive and the invalidation of every decision of a cycle, and the length of the motive and the choice of the
decisions of the memory of every configuration version saved before them.

The decisions recorded before keep both empty: the agent gave neither, and their memory gives the start of the
reasoning. The versions saved before, with the memory on or off, get a length of 160 characters and only openings,
closings and reversals, as a new flow gets them unless the user chooses otherwise; no new version is created. R5.3.5,
ADR memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni.

Revision ID: 0059
Revises: 0058
"""

import sqlalchemy as sa
from alembic import op

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cycle_decisions", sa.Column("motive", sa.Text))
    op.add_column("cycle_decisions", sa.Column("invalidation", sa.Text))
    _every_version(
        "UPDATE flow_versions SET configuration = jsonb_set(configuration::jsonb, '{memory}',"
        """ '{"text_length": 160, "all_decisions": false}'::jsonb || (configuration::jsonb -> 'memory'))::json """
        "WHERE configuration::jsonb ? 'memory'"
    )


def downgrade() -> None:
    _every_version(
        "UPDATE flow_versions SET configuration = jsonb_set(configuration::jsonb, '{memory}',"
        " (configuration::jsonb -> 'memory') - 'text_length' - 'all_decisions')::json "
        "WHERE configuration::jsonb ? 'memory'"
    )
    op.drop_column("cycle_decisions", "invalidation")
    op.drop_column("cycle_decisions", "motive")


def _every_version(statement: str) -> None:
    # Row level security forced on the table hides every row from the owner too, without a tenant: the versions of
    # every tenant change only while it is lifted, inside the transaction of the migration.
    op.execute("ALTER TABLE flow_versions NO FORCE ROW LEVEL SECURITY")
    op.execute(statement)
    op.execute("ALTER TABLE flow_versions FORCE ROW LEVEL SECURITY")
