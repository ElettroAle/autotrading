from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_return import FlowReturn
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

FLOW_ID = FlowId.new()
STARTED_AT = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
USER = UserId("anna")


def a_change(  # noqa: PLR0917 - one argument per value of a change
    reason: CapitalChangeReason,
    previous: str,
    new: str,
    amount: str,
    value_before: str | None,
    minutes: int = 30,
) -> CapitalChange:
    return CapitalChange(
        FLOW_ID,
        STARTED_AT + timedelta(minutes=minutes),
        Decimal(previous),
        Decimal(new),
        USER,
        reason,
        Decimal(amount),
        value_before=None if value_before is None else Decimal(value_before),
    )


def a_state(capital: str, value: str, *changes: CapitalChange) -> FlowState:
    cashed = sum((change.cashed_profit for change in changes), Decimal(0))
    realized = Decimal(value) - Decimal(capital) + cashed
    return FlowState(FLOW_ID, "USDC", Decimal(capital), (), realized, Decimal(0), Decimal(0), capital_changes=changes)


def a_snapshot(minutes: int, equity: str) -> EquitySnapshot:
    planned_at = STARTED_AT + timedelta(minutes=minutes)
    capital = Decimal(1000)
    return EquitySnapshot(
        FLOW_ID.value, planned_at, capital, Decimal(equity) - capital, Decimal(0), Decimal(0), Decimal(0)
    )


CASH_OUT = replace(a_change(CapitalChangeReason.CASH_OUT, "1000", "1000", "100", "1100"), cashed_profit=Decimal(100))


@pytest.mark.parametrize(
    ("initial", "current", "percent"),
    [
        ("300", "330", "10.00"),
        ("300", "270", "-10.00"),
        ("300", "300", "0.00"),
        ("300", "301", "0.33"),
        ("300", "300.0049", "0.00"),
        ("300", "299.9999", "0.00"),
    ],
)
def test_without_changes_the_return_is_the_change_of_the_capital_in_percent_with_two_decimals(
    initial: str, current: str, percent: str
) -> None:
    flow_return = FlowReturn(Decimal(initial), Decimal(current))

    assert str(flow_return.percent) == percent


def test_the_return_is_not_available_without_initial_capital() -> None:
    assert FlowReturn(Decimal(0), Decimal(10)).percent is None


def test_the_return_of_a_state_measures_its_total_value_against_the_capital_allocated_now() -> None:
    flow = a_flow(TenantId(uuid4()), configuration=a_configuration(assets=("BTC",), allocated_capital=Decimal(300)))
    activity = an_activity(positions=(a_position("BTC", margin=Decimal(50), unrealized_pnl=Decimal(20)),))
    state = FlowState.attributed(flow, activity, FlowTotals(flow.id, Decimal(15), Decimal(5), Decimal(0)))

    flow_return = FlowReturn.of(state)

    assert (flow_return.initial_capital, flow_return.current_capital) == (Decimal(300), Decimal(330))
    assert flow_return.percent == Decimal("10.00")


@pytest.mark.parametrize(
    ("capital", "value", "change", "percent"),
    [
        ("1000", "1000", CASH_OUT, "10.00"),
        ("1000", "1050", CASH_OUT, "15.50"),
        ("1900", "2000", a_change(CapitalChangeReason.INCREASE, "1000", "1900", "900", "1100"), "10.00"),
        ("1900", "2100", a_change(CapitalChangeReason.INCREASE, "1000", "1900", "900", "1100"), "15.50"),
        ("700", "600", a_change(CapitalChangeReason.REDUCTION, "1000", "700", "300", "900"), "-10.00"),
    ],
)
def test_the_return_compounds_the_periods_between_the_changes_of_the_capital(
    capital: str, value: str, change: CapitalChange, percent: str
) -> None:
    flow_return = FlowReturn.of(a_state(capital, value, change))

    assert flow_return.percent == Decimal(percent)


def test_the_chain_starts_from_the_capital_allocated_before_the_first_change() -> None:
    increase = a_change(CapitalChangeReason.INCREASE, "1000", "1900", "900", "1100")

    flow_return = FlowReturn.of(a_state("1900", "2100", increase))

    assert (flow_return.initial_capital, flow_return.current_capital, flow_return.changes) == (
        Decimal(1000),
        Decimal(2100),
        (increase,),
    )


def test_a_change_recorded_without_the_value_before_starts_the_chain_at_its_new_capital() -> None:
    legacy = a_change(CapitalChangeReason.INCREASE, "500", "1000", "500", None, minutes=10)
    increase = a_change(CapitalChangeReason.INCREASE, "1000", "1900", "900", "1100", minutes=20)

    flow_return = FlowReturn.of(a_state("1900", "2100", legacy, increase))

    assert (flow_return.initial_capital, flow_return.changes) == (Decimal(1000), (increase,))
    assert flow_return.percent == Decimal("15.50")


def test_a_flow_with_only_changes_recorded_without_the_value_before_keeps_the_return_on_the_capital_now() -> None:
    legacy = a_change(CapitalChangeReason.REDUCTION, "500", "300", "200", None)

    assert FlowReturn.of(a_state("300", "330", legacy)).percent == Decimal("10.00")


def test_the_changes_count_in_the_order_they_happened() -> None:
    later = a_change(CapitalChangeReason.REDUCTION, "1900", "1500", "400", "2000", minutes=50)
    earlier = a_change(CapitalChangeReason.INCREASE, "1000", "1900", "900", "1100", minutes=20)

    flow_return = FlowReturn.of(a_state("1500", "1760", later, earlier))

    assert flow_return.changes == (earlier, later)
    # 1100 / 1000, then 2000 / 2000, then 1760 / 1600
    assert flow_return.percent == Decimal("21.00")


def test_the_return_is_not_available_when_a_period_starts_without_value() -> None:
    emptied = a_change(CapitalChangeReason.REDUCTION, "1000", "500", "500", "500")

    assert FlowReturn(Decimal(1000), Decimal(10), (emptied,)).percent is None


def test_the_gain_sums_the_gains_of_the_periods_without_the_money_moved() -> None:
    increase = a_change(CapitalChangeReason.INCREASE, "1000", "1900", "900", "1100")

    assert FlowReturn.of(a_state("1900", "2100", increase)).gain == Decimal(200)


def test_over_a_curve_the_chain_goes_from_its_first_to_its_last_equity_through_the_changes_between() -> None:
    curve = (a_snapshot(0, "1000"), a_snapshot(15, "1100"), a_snapshot(45, "1050"))
    before = a_change(CapitalChangeReason.INCREASE, "500", "1000", "500", "500", minutes=-10)
    after = a_change(CapitalChangeReason.INCREASE, "1000", "1100", "100", "1050", minutes=50)
    legacy = a_change(CapitalChangeReason.INCREASE, "1000", "1000", "0", None, minutes=40)

    flow_return = FlowReturn.over(curve, (after, CASH_OUT, before, legacy))

    assert (flow_return.initial_capital, flow_return.current_capital, flow_return.changes) == (
        Decimal(1000),
        Decimal(1050),
        (CASH_OUT,),
    )
    assert flow_return.percent == Decimal("15.50")


def test_over_a_curve_a_change_at_its_first_point_is_already_in_its_equity() -> None:
    curve = (a_snapshot(30, "1000"), a_snapshot(45, "1050"))

    assert FlowReturn.over(curve, (CASH_OUT,)).changes == ()
