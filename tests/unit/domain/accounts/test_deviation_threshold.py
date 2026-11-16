from decimal import Decimal

import pytest

from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.accounts.errors import DeviationThresholdOutOfRangeError


def test_the_threshold_is_one_percent_when_not_given() -> None:
    assert DeviationThreshold.default().percent == Decimal(1)


@pytest.mark.parametrize("percent", ["0.1", "1", "3", "100"])
def test_a_threshold_from_a_tenth_to_a_hundred_is_admitted(percent: str) -> None:
    assert DeviationThreshold(Decimal(percent)).percent == Decimal(percent)


@pytest.mark.parametrize("percent", ["0", "0.09", "100.01", "101", "-1"])
def test_a_threshold_outside_the_range_is_refused(percent: str) -> None:
    with pytest.raises(DeviationThresholdOutOfRangeError) as raised:
        DeviationThreshold(Decimal(percent))

    assert str(raised.value) == "la soglia di scostamento va da 0,1 a 100"
    assert raised.value.status_code == 422
    assert raised.value.details == {"percent": percent}
