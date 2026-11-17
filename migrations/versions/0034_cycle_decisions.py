"""The decisions of the agent in every cycle, one row by asset, under row level security.

The cycles recorded before keep their decisions in the document of the decision step: the migration copies them, in
their order, with the confidence the agent gave or none when the decision came before it. R6.5.4, ADR
decisioni-del-ciclo-registrate-per-asset.

Revision ID: 0034
Revises: 0033
"""

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
# The document of the decision step as the journal of the cycle writes it: the decisions under the key "decisioni",
# each with the fields of the decision of the agent and the direction inside the fields of an opening (R1.4.6, R1.7.1).
RECORDED_DECISIONS = """
INSERT INTO cycle_decisions
    (flow_id, planned_at, position, tenant_id, asset, action, direction, confidence, reasoning)
SELECT
    cycles.flow_id,
    cycles.planned_at,
    decision.position - 1,
    cycles.tenant_id,
    decision.content ->> 'asset',
    decision.content ->> 'action',
    CASE WHEN decision.content ->> 'action' = 'apri' THEN decision.content -> 'opening' ->> 'direction' END,
    (decision.content ->> 'confidence')::integer,
    decision.content ->> 'reasoning'
FROM cycles
CROSS JOIN LATERAL jsonb_array_elements(cycles.documents) AS document(content)
CROSS JOIN LATERAL jsonb_array_elements(document.content -> 'content' -> 'decisioni')
    WITH ORDINALITY AS decision(content, position)
WHERE document.content ->> 'step' = 'agent_decision'
"""


def upgrade() -> None:
    op.create_table(
        "cycle_decisions",
        # One row for each decision of the cycle, in the order the agent gave them.
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("planned_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("position", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("asset", sa.Text, nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("direction", sa.Text),
        sa.Column("confidence", sa.Integer),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.ForeignKeyConstraint(["flow_id", "planned_at"], ["cycles.flow_id", "cycles.planned_at"]),
        sa.CheckConstraint("action IN ('apri', 'chiudi', 'mantieni', 'aggiorna')", name="cycle_decisions_action_known"),
        sa.CheckConstraint(
            "direction IS NULL OR (action = 'apri' AND direction IN ('long', 'short'))",
            name="cycle_decisions_direction_of_opening",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100", name="cycle_decisions_confidence_range"
        ),
    )
    op.execute("ALTER TABLE cycle_decisions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE cycle_decisions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY cycle_decisions_of_tenant ON cycle_decisions "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )
    _fill_from_the_recorded_cycles()
    # A decision is a fact of a recorded cycle: only ever added, never changed nor deleted (R1.7.1).
    op.execute(f"GRANT SELECT, INSERT ON cycle_decisions TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("cycle_decisions")


def _fill_from_the_recorded_cycles() -> None:
    # Row level security forced on the tables hides every row from the owner too, without a tenant: the cycles of
    # every tenant are copied only while it is lifted, inside the transaction of the migration.
    for table in ("cycles", "cycle_decisions"):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(RECORDED_DECISIONS)
    for table in ("cycles", "cycle_decisions"):
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
