"""The equity of a flow at a cycle, from the state attributed to it (R2.2.3, ADR 0120)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.equity_snapshot import EquitySnapshot, FlowEquity
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.trade_intent import TradeSide

PLANNED_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
FLOW_ID = FlowId.new()


def a_state(*, unrealized: tuple[Decimal, ...] = (), funding: Decimal = Decimal(0)) -> FlowState:
    positions = tuple(
        AccountPosition(asset, TradeSide.LONG, Decimal(1), Decimal(20), pnl, 1, Decimal(100))
        for asset, pnl in zip(("BTC", "ETH"), unrealized, strict=False)
    )
    return FlowState(FLOW_ID, "USDC", Decimal(300), positions, Decimal(4), Decimal(1), funding)


def test_the_equity_is_the_capital_plus_the_realized_and_unrealized_pnl_less_the_fees() -> None:
    snapshot = EquitySnapshot.of_state(PLANNED_AT, a_state(unrealized=(Decimal(2), Decimal(1))))

    assert snapshot.equity == Decimal(306)


def test_the_snapshot_keeps_every_part_of_the_equity() -> None:
    snapshot = EquitySnapshot.of_state(PLANNED_AT, a_state(unrealized=(Decimal(3),), funding=Decimal("-0.5")))

    assert snapshot == EquitySnapshot(
        flow_id=FLOW_ID.value,
        planned_at=PLANNED_AT,
        allocated_capital=Decimal(300),
        realized_pnl=Decimal(4),
        unrealized_pnl=Decimal(3),
        fees=Decimal(1),
        funding=Decimal("-0.5"),
    )


def test_the_equity_counts_the_funding_as_the_value_of_the_flow_does() -> None:
    state = a_state(unrealized=(Decimal(3),), funding=Decimal("-0.5"))

    snapshot = EquitySnapshot.of_state(PLANNED_AT, state)

    assert snapshot.equity == state.total_value == Decimal("305.5")


def test_the_equity_of_a_flow_starts_from_its_initial_capital() -> None:
    snapshot = EquitySnapshot.of_state(PLANNED_AT, a_state())

    equity = FlowEquity(Decimal(300), (snapshot,))

    assert (equity.initial_capital, equity.snapshots) == (Decimal(300), (snapshot,))


def a_snapshot_with_equity(equity: str, hours: int = 0) -> EquitySnapshot:
    return EquitySnapshot(
        FLOW_ID.value,
        PLANNED_AT + timedelta(hours=hours),
        Decimal(equity),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
    )


def test_each_point_changes_in_percent_from_the_first_point_of_the_period() -> None:
    first, second, third = (a_snapshot_with_equity(e, h) for h, e in enumerate(("200", "210", "190")))
    equity = FlowEquity(Decimal(500), (first, second, third))

    changes = [equity.change_percent(snapshot) for snapshot in equity.snapshots]

    assert changes == [Decimal(0), Decimal(5), Decimal(-5)]


def test_the_change_does_not_depend_on_the_initial_capital() -> None:
    first, second = a_snapshot_with_equity("300"), a_snapshot_with_equity("330", 1)

    assert FlowEquity(Decimal(100), (first, second)).change_percent(second) == Decimal(10)


def test_the_change_is_not_defined_when_the_first_point_has_no_equity() -> None:
    first, second = a_snapshot_with_equity("0"), a_snapshot_with_equity("10", 1)

    assert FlowEquity(Decimal(0), (first, second)).change_percent(second) is None
