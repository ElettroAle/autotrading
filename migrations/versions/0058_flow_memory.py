"""The memory of every configuration version saved before it existed, and the memory every cycle gave the agent.

The versions saved before get it off, with 10 decisions and 30 days, as a new flow gets it unless the user chooses
otherwise; no new version is created. The cycles recorded before keep it empty: no agent received a memory. R5.3.4, ADR
memoria-del-flusso-dalle-decisioni-operative-precedenti.

Revision ID: 0058
Revises: 0057
"""

import sqlalchemy as sa
from alembic import op

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _every_version(
        "UPDATE flow_versions SET configuration = (configuration::jsonb"
        """ || '{"memory": {"active": false, "decisions": 10, "days": 30}}'::jsonb)::json """
        "WHERE NOT configuration::jsonb ? 'memory'"
    )
    op.add_column("cycles", sa.Column("memory", sa.JSON))


def downgrade() -> None:
    op.drop_column("cycles", "memory")
    _every_version("UPDATE flow_versions SET configuration = (configuration::jsonb - 'memory')::json")


def _every_version(statement: str) -> None:
    # Row level security forced on the table hides every row from the owner too, without a tenant: the versions of
    # every tenant change only while it is lifted, inside the transaction of the migration.
    op.execute("ALTER TABLE flow_versions NO FORCE ROW LEVEL SECURITY")
    op.execute(statement)
    op.execute("ALTER TABLE flow_versions FORCE ROW LEVEL SECURITY")
