from decimal import Decimal

import pytest

from autotrading.domain.orders.errors import InvalidSlippageError
from autotrading.domain.orders.slippage import Slippage


def test_the_default_slippage_is_five_percent() -> None:
    assert Slippage.default().fraction == Decimal("0.05")


def test_a_percent_becomes_a_fraction() -> None:
    assert Slippage.percent(Decimal(1)).fraction == Decimal("0.01")


@pytest.mark.parametrize("fraction", [Decimal(0), Decimal(1), Decimal("-0.01"), Decimal("1.5")])
def test_a_slippage_outside_zero_and_one_is_refused(fraction: Decimal) -> None:
    with pytest.raises(InvalidSlippageError):
        Slippage(fraction)
