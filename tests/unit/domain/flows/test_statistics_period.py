from datetime import UTC, date, datetime, timedelta

import pytest

from autotrading.domain.flows.errors import InvalidStatisticsPeriodError
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind, TimeWindow

NOW = datetime(2026, 11, 14, 15, 30, tzinfo=UTC)


def test_the_whole_life_has_no_bounds() -> None:
    assert StatisticsPeriod.named("all").window(NOW) == TimeWindow()


def test_the_last_7_days_start_7_days_before_now() -> None:
    assert StatisticsPeriod.named("7d").window(NOW) == TimeWindow(since=NOW - timedelta(days=7))


def test_the_last_30_days_start_30_days_before_now() -> None:
    assert StatisticsPeriod.named("30d").window(NOW) == TimeWindow(since=NOW - timedelta(days=30))


def test_a_range_covers_its_first_and_last_day_in_utc() -> None:
    period = StatisticsPeriod.named("range", date(2026, 11, 1), date(2026, 11, 3))

    assert period.window(NOW) == TimeWindow(
        since=datetime(2026, 11, 1, tzinfo=UTC), until=datetime(2026, 11, 4, tzinfo=UTC)
    )


def test_a_range_of_one_day_is_valid() -> None:
    period = StatisticsPeriod.named("range", date(2026, 11, 1), date(2026, 11, 1))

    assert period.kind is StatisticsPeriodKind.RANGE


def test_an_unknown_period_is_rejected() -> None:
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        StatisticsPeriod.named("1y")

    assert raised.value.status_code == 400
    assert str(raised.value) == "periodo non valido: scegliere tra all, 7d, 30d, range"


@pytest.mark.parametrize(("first_day", "last_day"), [(None, date(2026, 11, 1)), (date(2026, 11, 1), None)])
def test_a_range_needs_both_days(first_day: date | None, last_day: date | None) -> None:
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        StatisticsPeriod.named("range", first_day, last_day)

    assert str(raised.value) == "periodo non valido: un intervallo ha il giorno iniziale e il giorno finale"


def test_a_range_cannot_end_before_it_starts() -> None:
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        StatisticsPeriod.named("range", date(2026, 11, 3), date(2026, 11, 1))

    assert str(raised.value) == "periodo non valido: il giorno iniziale è successivo al giorno finale"


@pytest.mark.parametrize("name", ["all", "7d", "30d"])
def test_only_a_range_takes_days(name: str) -> None:
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        StatisticsPeriod.named(name, date(2026, 11, 1), None)

    assert str(raised.value) == "periodo non valido: i giorni valgono solo per un intervallo"


def test_a_window_holds_the_instants_from_its_start_included_to_its_end_excluded() -> None:
    window = TimeWindow(since=NOW, until=NOW + timedelta(hours=1))

    assert window.contains(NOW)
    assert window.contains(NOW + timedelta(minutes=59))
    assert not window.contains(NOW + timedelta(hours=1))
    assert not window.contains(NOW - timedelta(seconds=1))


def test_a_window_without_bounds_holds_every_instant() -> None:
    assert TimeWindow().contains(datetime(2000, 1, 1, tzinfo=UTC))
