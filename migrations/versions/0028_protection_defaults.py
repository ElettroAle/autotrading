"""The stop loss and take profit defaults of every configuration version saved before they existed.

A stop loss of 5% from the entry price and no take profit, the same a new flow gets; no new version is created.
R3.1.2, ADR stop-loss-e-take-profit-predefiniti-del-flusso.

Revision ID: 0028
Revises: 0027
"""

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _every_version(
        "UPDATE flow_versions SET configuration = (configuration::jsonb"
        """ || '{"default_stop_loss_percent": "5", "default_take_profit_percent": null}'::jsonb)::json """
        "WHERE NOT configuration::jsonb ? 'default_stop_loss_percent'"
    )


def downgrade() -> None:
    _every_version(
        "UPDATE flow_versions SET configuration = (configuration::jsonb"
        " - ARRAY['default_stop_loss_percent', 'default_take_profit_percent'])::json"
    )


def _every_version(statement: str) -> None:
    # Row level security forced on the table hides every row from the owner too, without a tenant: the versions of
    # every tenant change only while it is lifted, inside the transaction of the migration.
    op.execute("ALTER TABLE flow_versions NO FORCE ROW LEVEL SECURITY")
    op.execute(statement)
    op.execute("ALTER TABLE flow_versions FORCE ROW LEVEL SECURITY")
