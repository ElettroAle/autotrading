"""The periods the user chooses for the equity curve of a flow (R2.2.3)."""

from datetime import UTC, datetime, timedelta

import pytest

from autotrading.domain.flows.equity_period import EquityPeriod, EquityWindow
from autotrading.domain.flows.errors import InvalidEquityRangeError

NOW = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)


def test_the_whole_life_of_the_flow_has_no_bounds() -> None:
    assert EquityPeriod.LIFETIME.window(NOW) == EquityWindow(None, None)


@pytest.mark.parametrize(("period", "days"), [(EquityPeriod.LAST_7_DAYS, 7), (EquityPeriod.LAST_30_DAYS, 30)])
def test_the_last_days_end_now(period: EquityPeriod, days: int) -> None:
    assert period.window(NOW) == EquityWindow(NOW - timedelta(days=days), None)


def test_the_last_days_ignore_the_bounds_of_a_range() -> None:
    assert EquityPeriod.LAST_7_DAYS.window(NOW, NOW - timedelta(days=1), NOW) == EquityWindow(
        NOW - timedelta(days=7), None
    )


def test_a_range_goes_from_its_start_included_to_its_end_excluded() -> None:
    start, end = NOW - timedelta(days=3), NOW - timedelta(days=1)

    assert EquityPeriod.RANGE.window(NOW, start, end) == EquityWindow(start, end)


@pytest.mark.parametrize(
    ("start", "end"),
    [(None, NOW), (NOW, None), (None, None)],
)
def test_a_range_needs_both_its_bounds(start: datetime | None, end: datetime | None) -> None:
    with pytest.raises(InvalidEquityRangeError, match="inizio e fine"):
        EquityPeriod.RANGE.window(NOW, start, end)


def test_a_range_starts_before_it_ends() -> None:
    with pytest.raises(InvalidEquityRangeError, match="l'inizio non precede la fine") as raised:
        EquityPeriod.RANGE.window(NOW, NOW, NOW - timedelta(days=1))

    assert raised.value.status_code == 422


def test_a_window_admits_the_instants_between_its_bounds() -> None:
    window = EquityWindow(NOW - timedelta(days=1), NOW)

    assert [window.admits(instant) for instant in (NOW - timedelta(days=2), NOW - timedelta(days=1), NOW)] == [
        False,
        True,
        False,
    ]


def test_a_window_without_bounds_admits_every_instant() -> None:
    assert EquityWindow(None, None).admits(NOW)
