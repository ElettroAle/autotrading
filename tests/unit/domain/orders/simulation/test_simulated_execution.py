from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import (
    InsufficientMarginError,
    LeverageAboveMaximumError,
    OrderBelowMinimumValueError,
    OrderSizeOffStepError,
    ReduceOnlyWithoutPositionError,
)
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition
from autotrading.domain.orders.slippage import Slippage

AT = datetime(2026, 11, 22, 12, tzinfo=UTC)
FEE_RATE = Decimal("0.00045")
ENGINE = SimulatedExecution(Slippage(Decimal("0.001")))


def a_market(price: Decimal = Decimal(90000)) -> Market:
    return Market("BTC", 40, 5, price, Decimal(10), price_significant_figures=5, taker_fee_rate=FEE_RATE)


def an_order(size: str = "0.00222", direction: Direction = Direction.LONG, *, reduce_only: bool = False) -> MarketOrder:
    return MarketOrder("BTC", direction, Decimal(size), Slippage.default(), reduce_only=reduce_only)


def an_account(*positions: SimulatedPosition, balance: Decimal = Decimal(1000)) -> SimulatedAccount:
    return SimulatedAccount(balance, positions)


def a_long(size: str = "0.00222", leverage: int = 2) -> SimulatedPosition:
    return SimulatedPosition(
        "BTC", Direction.LONG, Decimal(size), leverage, Decimal(90000), Decimal("99.9"), Decimal("0.0125")
    )


def test_an_opening_buys_at_the_current_price_with_the_slippage() -> None:
    trade = ENGINE.market_order(an_account(), a_market(), an_order(), 2, AT)

    assert trade.fill.price == Decimal(90090)
    assert trade.fill.size == Decimal("0.00222")
    assert trade.fill.is_buy


def test_an_opening_sell_executes_below_the_current_price() -> None:
    trade = ENGINE.market_order(an_account(), a_market(), an_order(direction=Direction.SHORT), 2, AT)

    assert trade.fill.price == Decimal(89910)
    assert not trade.fill.is_buy


def test_the_slippage_never_goes_beyond_the_one_the_order_accepts() -> None:
    engine = SimulatedExecution(Slippage(Decimal("0.2")))

    trade = engine.market_order(an_account(), a_market(), an_order(), 2, AT)

    assert trade.fill.price == Decimal(94500)


def test_the_fee_is_the_rate_of_the_market_on_the_executed_value() -> None:
    trade = ENGINE.market_order(an_account(), a_market(), an_order(), 2, AT)

    assert trade.fill.fee == Decimal("0.00222") * Decimal(90090) * FEE_RATE


def test_an_opening_takes_only_the_fee_from_the_balance() -> None:
    trade = ENGINE.market_order(an_account(), a_market(), an_order(), 2, AT)

    assert trade.account.balance == Decimal(1000) - trade.fill.fee


def test_an_opening_holds_the_margin_of_its_leverage() -> None:
    trade = ENGINE.market_order(an_account(), a_market(), an_order(), 2, AT)

    position = trade.account.position_of("BTC")
    assert position is not None
    assert position.margin == Decimal("0.00222") * Decimal(90090) / 2
    assert position.leverage == 2
    assert position.entry_price == Decimal(90090)
    assert trade.account.available_margin == trade.account.balance - position.margin


def test_the_maintenance_rate_is_half_the_margin_at_the_maximum_leverage() -> None:
    trade = ENGINE.market_order(an_account(), a_market(), an_order(), 2, AT)

    position = trade.account.position_of("BTC")
    assert position is not None
    assert position.maintenance_rate == Decimal("0.0125")


def test_an_order_below_the_minimum_value_is_refused() -> None:
    with pytest.raises(OrderBelowMinimumValueError):
        ENGINE.market_order(an_account(), a_market(), an_order("0.0001"), 2, AT)


def test_a_size_off_the_step_is_refused() -> None:
    with pytest.raises(OrderSizeOffStepError):
        ENGINE.market_order(an_account(), a_market(), an_order("0.000221"), 2, AT)


def test_a_leverage_above_the_maximum_is_refused() -> None:
    with pytest.raises(LeverageAboveMaximumError):
        ENGINE.market_order(an_account(), a_market(), an_order(), 50, AT)


def test_an_opening_beyond_the_available_margin_is_refused() -> None:
    with pytest.raises(InsufficientMarginError):
        ENGINE.market_order(an_account(balance=Decimal(50)), a_market(), an_order(), 2, AT)


def test_a_reduce_only_order_without_a_position_is_refused() -> None:
    with pytest.raises(ReduceOnlyWithoutPositionError):
        ENGINE.market_order(an_account(), a_market(), an_order(reduce_only=True), 2, AT)


def test_a_reduce_only_order_in_the_direction_of_the_position_finds_nothing_to_reduce() -> None:
    account = an_account(
        SimulatedPosition("BTC", Direction.SHORT, Decimal("0.001"), 2, Decimal(90000), Decimal(45), Decimal("0.0125"))
    )

    with pytest.raises(ReduceOnlyWithoutPositionError):
        ENGINE.market_order(account, a_market(), an_order(reduce_only=True), 2, AT)


def test_closing_realizes_the_pnl_and_releases_the_margin() -> None:
    trade = ENGINE.market_order(an_account(a_long()), a_market(Decimal(91000)), an_order(reduce_only=True), 2, AT)

    exit_price = Decimal(91000) * (1 - Decimal("0.001"))
    assert trade.fill.price == exit_price
    assert trade.fill.realized_pnl == (exit_price - Decimal(90000)) * Decimal("0.00222")
    assert trade.account.position_of("BTC") is None
    assert trade.account.balance == Decimal(1000) + trade.fill.realized_pnl - trade.fill.fee


def test_a_closing_never_goes_beyond_the_position() -> None:
    trade = ENGINE.market_order(an_account(a_long()), a_market(), an_order("0.01", reduce_only=True), 2, AT)

    assert trade.fill.size == Decimal("0.00222")


def test_a_closing_below_the_minimum_value_is_admitted() -> None:
    trade = ENGINE.market_order(an_account(a_long("0.0001")), a_market(), an_order("0.0001", reduce_only=True), 2, AT)

    assert trade.account.position_of("BTC") is None


def test_a_partial_closing_keeps_the_rest_with_its_share_of_the_margin() -> None:
    trade = ENGINE.market_order(an_account(a_long("0.004")), a_market(), an_order("0.001", reduce_only=True), 2, AT)

    position = trade.account.position_of("BTC")
    assert position is not None
    assert position.size == Decimal("0.003")
    assert position.margin == Decimal("99.9") * Decimal("0.003") / Decimal("0.004")


def test_an_opening_on_the_same_side_adds_at_the_average_price() -> None:
    trade = ENGINE.market_order(an_account(a_long()), a_market(), an_order(), 2, AT)

    position = trade.account.position_of("BTC")
    assert position is not None
    assert position.size == Decimal("0.00444")
    assert position.entry_price == (Decimal(90000) + Decimal(90090)) / 2
    assert position.margin == Decimal("99.9") + Decimal("0.00222") * Decimal(90090) / 2


def test_an_opening_on_the_other_side_closes_first_and_opens_the_rest() -> None:
    trade = ENGINE.market_order(an_account(a_long()), a_market(), an_order("0.00444", Direction.SHORT), 2, AT)

    position = trade.account.position_of("BTC")
    assert position is not None
    assert position.direction is Direction.SHORT
    assert position.size == Decimal("0.00222")
    assert trade.fill.realized_pnl == (Decimal(89910) - Decimal(90000)) * Decimal("0.00222")


def test_the_fill_records_the_position_before_it() -> None:
    trade = ENGINE.market_order(an_account(a_long()), a_market(), an_order(reduce_only=True), 2, AT)

    assert trade.fill.start_position == Decimal("0.00222")
    assert trade.fill.executed_at == AT
    assert not trade.fill.liquidation


def test_a_stop_loss_of_a_long_is_hit_at_or_below_its_price() -> None:
    stop = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.LONG, Decimal(88000))

    assert ENGINE.triggered(stop, Decimal(88000))
    assert not ENGINE.triggered(stop, Decimal(88001))


def test_a_take_profit_of_a_long_is_hit_at_or_above_its_price() -> None:
    target = ProtectionOrder("BTC", ProtectionKind.TAKE_PROFIT, Direction.LONG, Decimal(95000))

    assert ENGINE.triggered(target, Decimal(95000))
    assert not ENGINE.triggered(target, Decimal(94999))


def test_a_stop_loss_of_a_short_is_hit_at_or_above_its_price() -> None:
    stop = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.SHORT, Decimal(92000))

    assert ENGINE.triggered(stop, Decimal(92000))
    assert not ENGINE.triggered(stop, Decimal(91999))


def test_a_take_profit_of_a_short_is_hit_at_or_below_its_price() -> None:
    target = ProtectionOrder("BTC", ProtectionKind.TAKE_PROFIT, Direction.SHORT, Decimal(85000))

    assert ENGINE.triggered(target, Decimal(85000))
    assert not ENGINE.triggered(target, Decimal(85001))


def test_a_protection_closes_the_whole_position_at_the_market() -> None:
    stop = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.LONG, Decimal(88000))

    trade = ENGINE.protection(an_account(a_long()), a_market(Decimal(88000)), stop, AT)

    assert trade.account.position_of("BTC") is None
    assert trade.fill.realized_pnl < 0
    assert trade.account.balance == Decimal(1000) + trade.fill.realized_pnl - trade.fill.fee


def test_a_liquidation_loses_the_margin_at_the_liquidation_price_without_fee() -> None:
    position = a_long(leverage=10)

    trade = ENGINE.liquidation(an_account(position), position, AT)

    assert trade.fill.liquidation
    assert trade.fill.price == position.liquidation_price
    assert trade.fill.fee == 0
    assert trade.account.position_of("BTC") is None
    assert trade.account.balance == Decimal(1000) + trade.fill.realized_pnl


def test_a_liquidation_never_takes_more_than_the_margin() -> None:
    position = a_long(leverage=10)

    trade = ENGINE.liquidation(an_account(position), position, AT)

    assert trade.fill.realized_pnl >= -position.margin
