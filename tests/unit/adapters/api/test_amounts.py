from decimal import Decimal

import pytest

from autotrading.adapters.inbound.api.amounts import amount_text


@pytest.mark.parametrize(
    ("amount", "text"),
    [(Decimal("1000.00"), "1000"), (Decimal("1E+3"), "1000"), (Decimal("0.50"), "0.5"), (Decimal("-0.00"), "0")],
)
def test_an_api_amount_has_a_point_without_trailing_zeros_nor_exponent(amount: Decimal, text: str) -> None:
    assert amount_text(amount) == text
