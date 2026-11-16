from decimal import Decimal

import pytest

from autotrading.domain.flows.balance_comparison import BalanceComparison
from tests.support.activity import READ_AT


def compared(expected: str, read: str) -> BalanceComparison:
    return BalanceComparison(Decimal(expected), Decimal(read), READ_AT)


def test_the_difference_is_the_read_balance_less_the_expected_one() -> None:
    assert compared("1000", "995").difference == Decimal(-5)


def test_the_deviation_is_measured_in_percent_of_the_expected_balance_either_way() -> None:
    assert compared("1000", "980").deviation_percent == Decimal(2)
    assert compared("1000", "1020").deviation_percent == Decimal(2)


def test_the_deviation_keeps_four_decimals() -> None:
    assert compared("3000", "2999").deviation_percent == Decimal("0.0333")


@pytest.mark.parametrize(
    ("read", "threshold", "exceeds"), [("980", "1", True), ("990", "1", False), ("980", "3", False)]
)
def test_only_a_deviation_beyond_the_threshold_exceeds_it(read: str, threshold: str, exceeds: bool) -> None:
    assert compared("1000", read).exceeds(Decimal(threshold)) is exceeds


def test_without_an_expected_balance_any_difference_exceeds_every_threshold() -> None:
    assert compared("0", "1").exceeds(Decimal(100)) is True
    assert compared("0", "1").deviation_percent == Decimal(100)


def test_without_an_expected_balance_nothing_read_is_no_deviation() -> None:
    assert compared("0", "0").exceeds(Decimal("0.1")) is False
    assert compared("0", "0").deviation_percent == Decimal(0)
