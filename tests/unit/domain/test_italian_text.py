from decimal import Decimal

import pytest

from autotrading.domain.italian_text import money_text, number_text


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (Decimal("40.00"), "40"),
        (Decimal("0.5"), "0,5"),
        (Decimal("1E+3"), "1000"),
        (Decimal("4.20"), "4,2"),
        (Decimal("-0.00"), "0"),
        (Decimal("0.00016"), "0,00016"),
    ],
)
def test_a_number_reads_with_a_decimal_comma_without_trailing_zeros_nor_exponent(value: Decimal, text: str) -> None:
    assert number_text(value) == text


@pytest.mark.parametrize(
    ("amount", "text"),
    [
        (Decimal(2), "2"),
        (Decimal("1000.00"), "1000"),
        (Decimal("1E+3"), "1000"),
        (Decimal("4.2"), "4,20"),
        (Decimal("150.5"), "150,50"),
        (Decimal("0.04"), "0,04"),
        (Decimal("0.0123"), "0,0123"),
        (Decimal("-7.5"), "-7,50"),
        (Decimal("-0.00"), "0"),
    ],
)
def test_money_reads_whole_or_with_at_least_the_cents(amount: Decimal, text: str) -> None:
    assert money_text(amount) == text
