"""The first start of every flow, and the PnL the exchange reported for every closed position.

Bug 160 (ADR 0069), Bug 161 (ADR 0070).

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _first_start()
    op.add_column("closed_positions", sa.Column("realized_pnl", sa.Numeric))


def _first_start() -> None:
    op.add_column("flows", sa.Column("first_started_at", sa.DateTime(timezone=True)))
    # A flow already started began at its first cycle, or at its anchor when no cycle ran yet.
    op.execute(
        """
        UPDATE flows SET first_started_at = COALESCE(
            (SELECT MIN(cycles.planned_at) FROM cycles WHERE cycles.flow_id = flows.id),
            flows.cycle_anchor
        )
        WHERE flows.cycle_anchor IS NOT NULL
        """
    )
    # The database stamps the first start once, at the first change into "active", whoever changes the status:
    # a resume moves the anchor of the cycles, never the beginning of the flow (R1.4.3).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION flows_follow_status() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.status = 'active' AND OLD.status IS DISTINCT FROM 'active' THEN
                NEW.cycle_anchor := clock_timestamp();
                NEW.first_started_at := COALESCE(OLD.first_started_at, NEW.cycle_anchor);
            END IF;
            IF NEW.status <> 'paused' THEN
                NEW.pause_reason := NULL;
            END IF;
            RETURN NEW;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION flows_follow_status() RETURNS trigger LANGUAGE plpgsql AS $$
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
    op.drop_column("closed_positions", "realized_pnl")
    op.drop_column("flows", "first_started_at")
