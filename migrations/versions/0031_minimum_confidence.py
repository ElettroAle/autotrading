"""The minimum confidence of every configuration version saved before it existed.

None, the same a new flow gets unless the user sets one: every opening goes on whatever the confidence of the agent;
no new version is created. R3.1.4, ADR confidenza-nella-decisione-e-confidenza-minima.

Revision ID: 0031
Revises: 0030
"""

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _every_version(
        "UPDATE flow_versions SET configuration = (configuration::jsonb"
        """ || '{"minimum_confidence": null}'::jsonb)::json """
        "WHERE NOT configuration::jsonb ? 'minimum_confidence'"
    )


def downgrade() -> None:
    _every_version("UPDATE flow_versions SET configuration = (configuration::jsonb - 'minimum_confidence')::json")


def _every_version(statement: str) -> None:
    # Row level security forced on the table hides every row from the owner too, without a tenant: the versions of
    # every tenant change only while it is lifted, inside the transaction of the migration.
    op.execute("ALTER TABLE flow_versions NO FORCE ROW LEVEL SECURITY")
    op.execute(statement)
    op.execute("ALTER TABLE flow_versions FORCE ROW LEVEL SECURITY")
