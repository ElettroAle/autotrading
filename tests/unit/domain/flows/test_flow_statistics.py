from datetime import UTC, datetime, timedelta
from decimal import Decimal

from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_cost import FlowCost
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_statistics import FlowStatistics
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

CLOSED = datetime(2026, 11, 12, 10, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = FlowId.new()
NO_COST = FlowCost(Decimal(0), (), 0)
CYCLE = timedelta(minutes=15)


def closed(net_pnl: str, fees: str = "0") -> ClosedPosition:
    return ClosedPosition(
        tenant_id=TENANT,
        flow_id=FLOW,
        asset="BTC",
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(50),
        opening=PositionEnd(Decimal(100), CLOSED - timedelta(hours=1)),
        closing=PositionEnd(Decimal(100), CLOSED),
        fees=Decimal(fees),
        reason=CloseReason.AGENT,
        realized_pnl=Decimal(net_pnl) + Decimal(fees),
    )


def values(*equities: str) -> list[EquitySnapshot]:
    """The value of the flow at each cycle of the period, one cycle apart."""
    zero = Decimal(0)
    return [
        EquitySnapshot(FLOW.value, CLOSED + index * CYCLE, Decimal(equity), zero, zero, zero, zero)
        for index, equity in enumerate(equities)
    ]


def cash_out(at: datetime, amount: str, value_before: str) -> CapitalChange:
    capital = Decimal(1000)
    return CapitalChange(
        FLOW,
        at,
        capital,
        capital,
        UserId("anna"),
        CapitalChangeReason.CASH_OUT,
        Decimal(amount),
        value_before=Decimal(value_before),
        cashed_profit=Decimal(amount),
    )


def test_a_position_with_positive_net_result_is_won_and_with_negative_is_lost() -> None:
    statistics = FlowStatistics.of([closed("20"), closed("10"), closed("-6"), closed("-4")], NO_COST)

    assert (statistics.won, statistics.lost, statistics.operations) == (2, 2, 4)


def test_the_win_rate_is_won_over_won_and_lost_in_percent() -> None:
    statistics = FlowStatistics.of([closed("20"), closed("10"), closed("-6")], NO_COST)

    assert statistics.win_rate_percent is not None
    assert round(statistics.win_rate_percent, 2) == Decimal("66.67")


def test_a_position_even_is_neither_won_nor_lost_but_counts_as_operation() -> None:
    statistics = FlowStatistics.of([closed("20"), closed("-4"), closed("0")], NO_COST)

    assert (statistics.won, statistics.lost, statistics.operations) == (1, 1, 3)
    assert statistics.win_rate_percent == Decimal(50)


def test_the_net_result_takes_away_the_fees() -> None:
    # 1 USDC earned before fees of 1 USDC: an even position, not a won one.
    statistics = FlowStatistics.of([closed("0", fees="1")], NO_COST)

    assert (statistics.won, statistics.lost, statistics.operations) == (0, 0, 1)


def test_the_averages_are_the_mean_net_results_of_winners_and_losers() -> None:
    statistics = FlowStatistics.of([closed("20"), closed("10"), closed("-6"), closed("-4")], NO_COST)

    assert statistics.average_winning_pnl == Decimal(15)
    assert statistics.average_losing_pnl == Decimal(-5)


def test_the_fees_are_the_total_of_the_positions() -> None:
    statistics = FlowStatistics.of([closed("20", fees="1.5"), closed("-4", fees="1.5")], NO_COST)

    assert statistics.total_fees == Decimal(3)


def test_the_model_cost_is_the_total_of_the_calls_with_the_calls_without_cost_apart() -> None:
    statistics = FlowStatistics.of([], FlowCost(Decimal("1.20"), (), 2))

    assert statistics.model_cost_usd == Decimal("1.20")
    assert statistics.model_calls_without_cost == 2


def test_without_operations_nothing_is_available_but_the_counts() -> None:
    statistics = FlowStatistics.of([], NO_COST)

    assert (statistics.won, statistics.lost, statistics.operations) == (0, 0, 0)
    assert statistics.win_rate_percent is None
    assert statistics.average_winning_pnl is None
    assert statistics.average_losing_pnl is None
    assert statistics.total_fees == Decimal(0)


def test_with_only_even_positions_the_win_rate_is_not_available() -> None:
    statistics = FlowStatistics.of([closed("0"), closed("0")], NO_COST)

    assert statistics.operations == 2
    assert statistics.win_rate_percent is None


def test_the_net_pnl_is_the_sum_of_the_net_results_of_the_operations() -> None:
    statistics = FlowStatistics.of([closed("20", fees="1"), closed("-6", fees="0.5"), closed("0")], NO_COST)

    assert statistics.net_pnl == Decimal(14)


def test_the_net_pnl_is_zero_without_operations() -> None:
    assert FlowStatistics.of([], NO_COST).net_pnl == Decimal(0)


def test_the_return_goes_from_the_first_value_of_the_period_to_the_last() -> None:
    statistics = FlowStatistics.of([], NO_COST, values("1000", "1200", "1080"))

    assert statistics.return_percent == Decimal("8.00")


def test_the_return_is_compounded_across_the_changes_of_the_capital_in_the_period() -> None:
    # ADR rendimento-del-periodo-nelle-statistiche: 1000 to 1100, a cash-out of 100, then 1000 to 1050.
    equity = values("1000", "1000", "1050")
    change = cash_out(CLOSED + CYCLE / 2, "100", "1100")

    statistics = FlowStatistics.of([], NO_COST, equity, (change,))

    assert statistics.return_percent == Decimal("15.50")


def test_a_change_before_the_period_does_not_move_its_return() -> None:
    equity = values("1000", "1050")
    before = cash_out(CLOSED - CYCLE, "100", "1100")

    statistics = FlowStatistics.of([], NO_COST, equity, (before,))

    assert statistics.return_percent == Decimal("5.00")


def test_the_return_is_not_available_without_values_in_the_period() -> None:
    statistics = FlowStatistics.of([closed("20")], NO_COST, (), (cash_out(CLOSED, "100", "1100"),))

    assert statistics.return_percent is None
