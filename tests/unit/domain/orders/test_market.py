from decimal import Decimal

import pytest

from autotrading.domain.orders.errors import (
    InvalidLeverageError,
    InvalidMarketError,
    LeverageAboveMaximumError,
    OrderSizeBelowStepError,
)
from autotrading.domain.orders.market import Market

BTC = Market("BTC", max_leverage=40, size_decimals=5, mid_price=Decimal(100000), min_order_value=Decimal(10))


def test_a_leverage_up_to_the_maximum_is_accepted() -> None:
    BTC.require_leverage(1)
    BTC.require_leverage(40)


def test_rejects_leverage_above_exchange_maximum() -> None:
    with pytest.raises(LeverageAboveMaximumError) as raised:
        BTC.require_leverage(41)

    assert raised.value.maximum == 40
    assert str(raised.value) == "leva oltre il massimo dell'exchange per BTC: 40"


@pytest.mark.parametrize("leverage", [0, -2])
def test_rejects_a_leverage_below_one(leverage: int) -> None:
    with pytest.raises(InvalidLeverageError):
        BTC.require_leverage(leverage)


def test_the_size_step_follows_the_decimals_of_the_asset() -> None:
    assert BTC.size_step == Decimal("0.00001")
    assert Market("ETH", 25, 0, Decimal(4000), Decimal(10)).size_step == Decimal(1)


def test_the_size_is_the_value_at_the_current_price_rounded_down_to_the_step() -> None:
    assert BTC.size_for(Decimal("23.4567")) == Decimal("0.00023")


def test_the_size_is_not_rounded_up_when_rounding_down_meets_the_minimum() -> None:
    assert BTC.size_for(Decimal("23.9999")) == Decimal("0.00023")


def test_a_value_below_one_step_is_refused() -> None:
    with pytest.raises(OrderSizeBelowStepError) as raised:
        BTC.size_for(Decimal("0.99"))

    assert raised.value.step == Decimal("0.00001")


@pytest.mark.parametrize(
    ("max_leverage", "size_decimals", "mid_price"), [(0, 5, Decimal(1)), (40, -1, Decimal(1)), (40, 5, Decimal(0))]
)
def test_metadata_out_of_range_are_refused(max_leverage: int, size_decimals: int, mid_price: Decimal) -> None:
    with pytest.raises(InvalidMarketError):
        Market("BTC", max_leverage, size_decimals, mid_price, Decimal(10))


ROUNDING = Market("BTC", max_leverage=40, size_decimals=5, mid_price=Decimal(60123), min_order_value=Decimal(10))


def test_a_value_at_the_minimum_is_rounded_up_when_rounding_down_would_fall_below_it() -> None:
    assert ROUNDING.size_for(Decimal(10)) == Decimal("0.00017")


def test_a_value_above_the_minimum_is_rounded_up_when_rounding_down_would_fall_below_it() -> None:
    assert ROUNDING.size_for(Decimal("10.2")) == Decimal("0.00017")


def test_rounding_down_that_stays_at_the_minimum_is_kept() -> None:
    assert ROUNDING.size_for(Decimal("10.3")) == Decimal("0.00017")
    assert Market("BTC", 40, 5, Decimal(100000), Decimal(10)).size_for(Decimal(10)) == Decimal("0.0001")


def test_a_value_below_the_minimum_is_never_rounded_up() -> None:
    assert ROUNDING.size_for(Decimal("9.99")) == Decimal("0.00016")


def test_a_negative_minimum_is_refused() -> None:
    with pytest.raises(InvalidMarketError):
        Market("BTC", 40, 5, Decimal(1), Decimal(-1))


def test_rounding_down_to_exactly_the_minimum_is_kept() -> None:
    assert Market("BTC", 40, 5, Decimal(100000), Decimal(10)).size_for(Decimal("10.5")) == Decimal("0.0001")


def test_an_exchange_without_a_minimum_is_admitted() -> None:
    assert Market("BTC", 40, 5, Decimal(100000), Decimal(0)).size_for(Decimal("10.5")) == Decimal("0.0001")
