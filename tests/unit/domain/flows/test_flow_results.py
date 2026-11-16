"""How a flow is doing at a glance (R6.4.2, ADR riepilogo-dei-risultati-nell-api)."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_results import FlowResults
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.user_id import UserId

FLOW_ID = FlowId.new()
FIRST_CYCLE = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)


def a_state(
    *, capital: Decimal = Decimal(100), realized: Decimal = Decimal(0), assets: tuple[str, ...] = ()
) -> FlowState:
    positions = tuple(
        AccountPosition(asset, TradeSide.LONG, Decimal(1), Decimal(20), Decimal(0), 1, Decimal(10), Decimal(10))
        for asset in assets
    )
    return FlowState(FLOW_ID, "USDC", capital, positions, realized, Decimal(0), Decimal(0))


def a_snapshot(hours: int, equity: Decimal) -> EquitySnapshot:
    planned_at = FIRST_CYCLE + timedelta(hours=hours)
    return EquitySnapshot(
        FLOW_ID.value, planned_at, Decimal(100), equity - Decimal(100), Decimal(0), Decimal(0), Decimal(0)
    )


def test_the_total_gain_is_the_value_of_the_flow_less_its_initial_capital_also_in_percent() -> None:
    results = FlowResults.of(a_state(realized=Decimal("2.5")), (), 0)

    assert (results.total_gain, results.total_gain_percent) == (Decimal("2.5"), Decimal("2.50"))


def a_cash_out(hours: float, profit: Decimal, capital: Decimal = Decimal(100)) -> CapitalChange:
    return CapitalChange(
        FLOW_ID,
        FIRST_CYCLE + timedelta(hours=hours),
        capital,
        capital,
        UserId("anna"),
        CapitalChangeReason.CASH_OUT,
        profit,
        value_before=capital + profit,
        cashed_profit=profit,
    )


def test_the_total_gain_keeps_the_profits_cashed_out() -> None:
    cashed_out = replace(a_state(realized=Decimal(30)), capital_changes=(a_cash_out(0, Decimal(30)),))

    assert FlowResults.of(cashed_out, (), 0).total_gain == Decimal(30)


def test_the_total_gain_in_percent_is_compounded_across_the_changes_of_the_capital() -> None:
    # ADR rendimento-composto-tra-le-variazioni-di-capitale: 10% before the cash-out, then 5%.
    cashed_out = replace(a_state(realized=Decimal(15)), capital_changes=(a_cash_out(0, Decimal(10)),))

    assert FlowResults.of(cashed_out, (), 0).total_gain_percent == Decimal("15.50")


def test_the_gain_in_the_period_leaves_out_the_money_the_changes_moved() -> None:
    state = replace(a_state(realized=Decimal(15)), capital_changes=(a_cash_out(1.5, Decimal(10)),))
    snapshots = (a_snapshot(0, Decimal(100)), a_snapshot(1, Decimal(110)), a_snapshot(2, Decimal(105)))

    results = FlowResults.of(state, snapshots, 0)

    assert (results.period_gain, results.period_gain_percent) == (Decimal(15), Decimal("15.00"))


def test_a_loss_is_a_negative_total_gain() -> None:
    results = FlowResults.of(a_state(realized=Decimal("-1.2")), (), 0)

    assert (results.total_gain, results.total_gain_percent) == (Decimal("-1.2"), Decimal("-1.20"))


def test_the_gain_in_the_period_goes_from_the_first_to_the_last_equity_recorded_in_it() -> None:
    snapshots = (a_snapshot(0, Decimal("102.1")), a_snapshot(1, Decimal("101.8")), a_snapshot(2, Decimal("102.5")))

    results = FlowResults.of(a_state(realized=Decimal("2.5")), snapshots, 0)

    assert (results.period_gain, results.period_gain_percent) == (Decimal("0.4"), Decimal("0.40"))


def test_a_period_without_recorded_equity_has_gained_nothing() -> None:
    results = FlowResults.of(a_state(), (), 0)

    assert (results.period_gain, results.period_gain_percent) == (Decimal(0), Decimal("0.00"))


def test_the_percents_are_not_available_without_initial_capital() -> None:
    results = FlowResults.of(a_state(capital=Decimal(0)), (a_snapshot(0, Decimal(1)), a_snapshot(1, Decimal(2))), 0)

    assert (results.total_gain_percent, results.period_gain_percent) == (None, None)


def test_the_results_count_the_open_positions_and_keep_the_failed_cycles_and_the_currency() -> None:
    results = FlowResults.of(a_state(assets=("BTC", "ETH")), (), 2)

    assert (results.open_positions, results.failed_cycles, results.currency) == (2, 2, "USDC")
