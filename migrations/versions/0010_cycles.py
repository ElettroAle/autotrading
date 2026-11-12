"""The cycles of the flows, their forecasts, and what the worker needs to plan them across tenants.

R1.2.1-R1.2.5, R1.3.5, ADR 0042.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
SCHEDULER_OF_TRANSACTION = "current_setting('app.scheduler', true) = 'on'"


def upgrade() -> None:
    _flows_for_the_scheduler()
    _cycles()
    _forecasts()


def _flows_for_the_scheduler() -> None:
    op.add_column("flows", sa.Column("cycle_anchor", sa.DateTime(timezone=True)))
    op.add_column("flows", sa.Column("pause_reason", sa.Text))
    # The first cycle falls at the start or the resume of the flow (R1.2.1): the database stamps the instant on
    # every change into "active", whoever changes the status; an automatic pause reason lasts while paused.
    op.execute(
        """
        CREATE FUNCTION flows_follow_status() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.status = 'active' AND OLD.status IS DISTINCT FROM 'active' THEN
                NEW.cycle_anchor := clock_timestamp();
            END IF;
            IF NEW.status <> 'paused' THEN
                NEW.pause_reason := NULL;
            END IF;
            RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER flows_follow_status BEFORE UPDATE OF status ON flows "
        "FOR EACH ROW EXECUTE FUNCTION flows_follow_status()"
    )
    # The worker plans the cycles of the whole installation: a transaction that declares itself the scheduler reads
    # the active flows of every tenant and their configurations, and nothing else, and only to read them.
    op.execute(
        f"CREATE POLICY flows_scheduled ON flows FOR SELECT USING (status = 'active' AND {SCHEDULER_OF_TRANSACTION})"
    )
    op.execute(
        "CREATE POLICY flow_versions_scheduled ON flow_versions FOR SELECT "
        f"USING ({SCHEDULER_OF_TRANSACTION} AND EXISTS (SELECT 1 FROM flows WHERE flows.id = flow_versions.flow_id))"
    )


def _cycles() -> None:
    op.create_table(
        "cycles",
        # One row per planned instant of a flow: of two executors, only the first one takes it (R1.2.2).
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("planned_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("outcome", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("delay_seconds", sa.Integer),
        sa.Column("steps", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("absent_sources", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("failure", postgresql.JSONB),
        sa.Column("recorded_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
        sa.CheckConstraint("outcome IN ('completed', 'failed', 'skipped')", name="cycles_outcome_known"),
    )
    _of_tenant("cycles")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON cycles TO {APPLICATION_ROLE}")


def _forecasts() -> None:
    op.create_table(
        "forecasts",
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("asset", sa.Text, primary_key=True),
        sa.Column("horizon_minutes", sa.Integer, primary_key=True),
        sa.Column("made_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("last_price", sa.Numeric, nullable=False),
        sa.Column("predicted_price", sa.Numeric, nullable=False),
        sa.Column("history_days", sa.Integer, nullable=False),
        sa.Column("shortened", sa.Boolean, nullable=False),
        sa.Column("actual_price", sa.Numeric),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
    )
    _of_tenant("forecasts")
    # A forecast is never deleted: the error of the forecasts is evaluated in a later epic (R1.3.5).
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON forecasts TO {APPLICATION_ROLE}")


def _of_tenant(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_of_tenant ON {table} "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )


def downgrade() -> None:
    op.drop_table("forecasts")
    op.drop_table("cycles")
    op.execute("DROP POLICY flow_versions_scheduled ON flow_versions")
    op.execute("DROP POLICY flows_scheduled ON flows")
    op.execute("DROP TRIGGER flows_follow_status ON flows")
    op.execute("DROP FUNCTION flows_follow_status()")
    op.drop_column("flows", "pause_reason")
    op.drop_column("flows", "cycle_anchor")
