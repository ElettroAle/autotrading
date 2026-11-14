from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from autotrading.adapters.outbound.sqlalchemy.equity_snapshot_repository import (
    of_flow_query,
    row_of,
    snapshot_of,
)
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId

PLANNED = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
TENANT = TenantId.new()
SNAPSHOT = EquitySnapshot(uuid4(), PLANNED, Decimal(300), Decimal(4), Decimal(3), Decimal(1), Decimal("-0.25"))


def test_a_snapshot_is_saved_with_its_equity_and_every_part_of_it() -> None:
    assert row_of(SNAPSHOT, TENANT) == {
        "tenant_id": TENANT.value,
        "flow_id": SNAPSHOT.flow_id,
        "planned_at": PLANNED,
        "equity": Decimal("305.75"),
        "allocated_capital": Decimal(300),
        "realized_pnl": Decimal(4),
        "unrealized_pnl": Decimal(3),
        "fees": Decimal(1),
        "funding": Decimal("-0.25"),
    }


def test_a_saved_snapshot_reads_back_the_same() -> None:
    assert snapshot_of(row_of(SNAPSHOT, TENANT)) == SNAPSHOT


def compiled(window: TimeWindow) -> str:
    return str(of_flow_query(SNAPSHOT.flow_id, window))


def test_the_curve_of_a_whole_life_reads_every_cycle_of_the_flow_from_the_oldest() -> None:
    text = compiled(TimeWindow(None, None))

    assert "equity_snapshots.flow_id = " in text
    assert "planned_at >=" not in text
    assert "planned_at <" not in text
    assert text.endswith("ORDER BY equity_snapshots.planned_at")


def test_the_curve_of_a_period_reads_the_cycles_between_its_bounds() -> None:
    text = compiled(TimeWindow(PLANNED - timedelta(days=7), PLANNED))

    assert "equity_snapshots.planned_at >= " in text
    assert "equity_snapshots.planned_at < " in text
