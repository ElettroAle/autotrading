"""The equity of every cycle of a flow, partitioned by month, under row level security.

The partitions of the months up to the end of 2030 exist from the start, and a default partition takes any instant
beyond them, so a cycle never fails for want of a partition; a later migration adds the months that follow.
R2.2.3, ADR 0120.

Revision ID: 0020
Revises: 0019
"""

from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

APPLICATION_ROLE = "autotrading_app"
TENANT_OF_TRANSACTION = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
FIRST_MONTH = date(2026, 11, 1)
LAST_MONTH = date(2030, 12, 1)


def _next_month(month: date) -> date:
    return date(month.year + month.month // 12, month.month % 12 + 1, 1)


def _months() -> list[date]:
    months, month = [], FIRST_MONTH
    while month <= LAST_MONTH:
        months.append(month)
        month = _next_month(month)
    return months


def _protect(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_of_tenant ON {table} "
        f"USING (tenant_id = {TENANT_OF_TRANSACTION}) WITH CHECK (tenant_id = {TENANT_OF_TRANSACTION})"
    )


def upgrade() -> None:
    op.create_table(
        "equity_snapshots",
        # One point for each planned cycle of the flow: the key carries the instant the partitions split on.
        sa.Column("flow_id", sa.Uuid, primary_key=True),
        sa.Column("planned_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("equity", sa.Numeric, nullable=False),
        sa.Column("allocated_capital", sa.Numeric, nullable=False),
        sa.Column("realized_pnl", sa.Numeric, nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric, nullable=False),
        sa.Column("fees", sa.Numeric, nullable=False),
        sa.Column("funding", sa.Numeric, nullable=False),
        sa.ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
        postgresql_partition_by="RANGE (planned_at)",
    )
    _protect("equity_snapshots")
    for month in _months():
        partition = f"equity_snapshots_{month:%Y_%m}"
        op.execute(
            f"CREATE TABLE {partition} PARTITION OF equity_snapshots "
            f"FOR VALUES FROM ('{month.isoformat()} 00:00+00') TO ('{_next_month(month).isoformat()} 00:00+00')"
        )
        _protect(partition)
    op.execute("CREATE TABLE equity_snapshots_default PARTITION OF equity_snapshots DEFAULT")
    _protect("equity_snapshots_default")
    # The equity of a cycle is a fact of the past: only ever added, read through the partitioned table alone.
    op.execute(f"GRANT SELECT, INSERT ON equity_snapshots TO {APPLICATION_ROLE}")


def downgrade() -> None:
    op.drop_table("equity_snapshots")
