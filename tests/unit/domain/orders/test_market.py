from decimal import Decimal

import pytest

from autotrading.domain.orders.errors import (
    InvalidLeverageError,
    InvalidMarketError,
    LeverageAboveMaximumError,
    OrderSizeBelowStepError,
)
from autotrading.domain.orders.market import Market

BTC = Market("BTC", max_leverage=40, size_decimals=5, mid_price=Decimal(100000))


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
    assert Market("ETH", 25, 0, Decimal(4000)).size_step == Decimal(1)


def test_the_size_is_the_value_at_the_current_price_rounded_down_to_the_step() -> None:
    assert BTC.size_for(Decimal("23.4567")) == Decimal("0.00023")


def test_the_size_is_never_rounded_up() -> None:
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
        Market("BTC", max_leverage, size_decimals, mid_price)
