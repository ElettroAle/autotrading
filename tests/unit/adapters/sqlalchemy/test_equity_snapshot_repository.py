from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from autotrading.adapters.outbound.sqlalchemy.equity_snapshot_repository import (
    daily_from_query,
    daily_until_query,
    of_flow_query,
    peak_query,
    row_of,
    snapshot_of,
)
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId

PLANNED = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
TENANT = TenantId.new()
SNAPSHOT = EquitySnapshot(
    uuid4(), PLANNED, Decimal(300), Decimal(14), Decimal(3), Decimal(1), Decimal("-0.25"), cashed_profit=Decimal(10)
)


def test_a_snapshot_is_saved_with_its_equity_and_every_part_of_it() -> None:
    assert row_of(SNAPSHOT, TENANT) == {
        "tenant_id": TENANT.value,
        "flow_id": SNAPSHOT.flow_id,
        "planned_at": PLANNED,
        "equity": Decimal("305.75"),
        "allocated_capital": Decimal(300),
        "realized_pnl": Decimal(14),
        "unrealized_pnl": Decimal(3),
        "fees": Decimal(1),
        "funding": Decimal("-0.25"),
        "cashed_profit": Decimal(10),
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


def test_the_daily_reference_is_the_last_equity_up_to_midnight() -> None:
    text = str(daily_until_query(SNAPSHOT.flow_id, PLANNED))

    assert "equity_snapshots.planned_at <= " in text
    assert text.endswith("ORDER BY equity_snapshots.planned_at DESC\n LIMIT :param_1")


def test_without_equity_before_midnight_the_daily_reference_is_the_first_of_the_day_up_to_now() -> None:
    text = str(daily_from_query(SNAPSHOT.flow_id, PLANNED, PLANNED + timedelta(hours=1)))

    assert "equity_snapshots.planned_at >= " in text
    assert "equity_snapshots.planned_at <= " in text
    assert text.endswith("ORDER BY equity_snapshots.planned_at\n LIMIT :param_1")


def test_the_peak_is_the_highest_gain_on_the_capital_from_the_instant_to_now_the_most_recent_first() -> None:
    text = str(peak_query(SNAPSHOT.flow_id, PLANNED, PLANNED + timedelta(days=1)))

    assert "equity_snapshots.planned_at >= " in text
    assert "equity_snapshots.planned_at <= " in text
    assert text.endswith(
        "ORDER BY equity_snapshots.equity - equity_snapshots.allocated_capital DESC, "
        "equity_snapshots.planned_at DESC\n LIMIT :param_1"
    )
