"""ADR intervallo-di-riconciliazione-del-conto: whole minutes from one to a day, five unless the user sets another."""

from datetime import timedelta

import pytest

from autotrading.domain.accounts.errors import ReconciliationIntervalOutOfRangeError
from autotrading.domain.accounts.reconciliation_interval import ReconciliationInterval


def test_the_interval_is_five_minutes_when_not_set() -> None:
    assert ReconciliationInterval.default().minutes == 5


def test_an_interval_left_empty_is_the_default() -> None:
    assert ReconciliationInterval.of(None) == ReconciliationInterval.default()
    assert ReconciliationInterval.of(15) == ReconciliationInterval(15)


@pytest.mark.parametrize("minutes", [1, 5, 15, 1440])
def test_an_interval_from_one_minute_to_a_day_is_admitted(minutes: int) -> None:
    interval = ReconciliationInterval(minutes)

    assert interval.minutes == minutes
    assert interval.duration == timedelta(minutes=minutes)


@pytest.mark.parametrize("minutes", [0, -1, 1441])
def test_an_interval_outside_the_range_is_refused(minutes: int) -> None:
    with pytest.raises(ReconciliationIntervalOutOfRangeError) as raised:
        ReconciliationInterval(minutes)

    assert str(raised.value) == "intervallo di riconciliazione da 1 a 1440 minuti"
    assert raised.value.status_code == 422
    assert raised.value.details == {"minutes": minutes}
