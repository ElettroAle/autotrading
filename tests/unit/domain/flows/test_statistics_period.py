from datetime import UTC, datetime, timedelta, timezone

import pytest

from autotrading.domain.flows.errors import InvalidStatisticsPeriodError
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind, TimeWindow

NOW = datetime(2026, 11, 14, 15, 30, tzinfo=UTC)
MINUTE = timedelta(minutes=1)


def test_the_whole_life_has_no_bounds() -> None:
    assert StatisticsPeriod.named("all").window(NOW) == TimeWindow()


# ADR periodi-brevi-come-durata-nel-dominio: a period of the last N holds the minutes from N before now to now.
@pytest.mark.parametrize(
    ("name", "duration"),
    [
        ("30m", timedelta(minutes=30)),
        ("1h", timedelta(hours=1)),
        ("6h", timedelta(hours=6)),
        ("12h", timedelta(hours=12)),
        ("24h", timedelta(hours=24)),
        ("7d", timedelta(days=7)),
        ("30d", timedelta(days=30)),
    ],
)
def test_a_period_of_the_last_n_holds_the_minutes_from_n_before_now_to_now(name: str, duration: timedelta) -> None:
    assert StatisticsPeriod.named(name).window(NOW) == TimeWindow(since=NOW - duration, until=NOW + MINUTE)


def test_the_last_hour_at_10_15_holds_from_9_15_included_to_the_current_minute() -> None:
    window = StatisticsPeriod.named("1h").window(datetime(2026, 11, 16, 10, 15, 42, tzinfo=UTC))

    assert window == TimeWindow(
        since=datetime(2026, 11, 16, 9, 15, tzinfo=UTC), until=datetime(2026, 11, 16, 10, 16, tzinfo=UTC)
    )
    assert window.contains(datetime(2026, 11, 16, 9, 15, tzinfo=UTC))
    assert not window.contains(datetime(2026, 11, 16, 9, 14, 59, tzinfo=UTC))


# ADR periodo-di-6-ore-e-dall-inizio: the last 6 hours at 10:15 hold from 4:15 included to the current minute.
def test_the_last_6_hours_at_10_15_hold_from_4_15_included_to_the_current_minute() -> None:
    window = StatisticsPeriod.named("6h").window(datetime(2026, 11, 16, 10, 15, 42, tzinfo=UTC))

    assert window == TimeWindow(
        since=datetime(2026, 11, 16, 4, 15, tzinfo=UTC), until=datetime(2026, 11, 16, 10, 16, tzinfo=UTC)
    )


def test_the_periods_go_from_the_shortest_to_the_range() -> None:
    assert [kind.value for kind in StatisticsPeriodKind] == [
        "30m",
        "1h",
        "6h",
        "12h",
        "24h",
        "7d",
        "30d",
        "all",
        "range",
    ]


# ADR periodo-al-minuto: a range and its window hold the minutes from the start to the end, both whole, in UTC.
def test_a_range_covers_its_minutes_from_the_first_to_the_last_both_whole() -> None:
    period = StatisticsPeriod.named(
        "range", datetime(2026, 11, 16, 9, 15, 42, tzinfo=UTC), datetime(2026, 11, 16, 11, 40, 7, tzinfo=UTC)
    )

    assert period.window(NOW) == TimeWindow(
        since=datetime(2026, 11, 16, 9, 15, tzinfo=UTC), until=datetime(2026, 11, 16, 11, 41, tzinfo=UTC)
    )


def test_a_range_within_one_minute_is_valid() -> None:
    period = StatisticsPeriod.named(
        "range", datetime(2026, 11, 1, 9, 15, 30, tzinfo=UTC), datetime(2026, 11, 1, 9, 15, 10, tzinfo=UTC)
    )

    assert period.kind is StatisticsPeriodKind.RANGE
    assert period.window(NOW) == TimeWindow(
        since=datetime(2026, 11, 1, 9, 15, tzinfo=UTC), until=datetime(2026, 11, 1, 9, 16, tzinfo=UTC)
    )


def test_an_unknown_period_is_rejected() -> None:
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        StatisticsPeriod.named("2h")

    assert raised.value.status_code == 400
    assert str(raised.value) == "periodo non valido: scegliere tra 30m, 1h, 6h, 12h, 24h, 7d, 30d, all, range"


@pytest.mark.parametrize(("since", "until"), [(None, NOW), (NOW, None)])
def test_a_range_needs_its_start_and_its_end(since: datetime | None, until: datetime | None) -> None:
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        StatisticsPeriod.named("range", since, until)

    assert str(raised.value) == "periodo non valido: un intervallo ha l'inizio e la fine"


def test_a_range_cannot_end_before_it_starts() -> None:
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        StatisticsPeriod.named("range", NOW, NOW - timedelta(minutes=1))

    assert str(raised.value) == "periodo non valido: l'inizio è successivo alla fine"


@pytest.mark.parametrize("name", ["30m", "1h", "6h", "12h", "24h", "7d", "30d", "all"])
def test_only_a_range_takes_a_start_and_an_end(name: str) -> None:
    with pytest.raises(InvalidStatisticsPeriodError) as raised:
        StatisticsPeriod.named(name, NOW, None)

    assert str(raised.value) == "periodo non valido: inizio e fine valgono solo per un intervallo"


def test_a_window_holds_the_instants_from_its_start_included_to_its_end_excluded() -> None:
    window = TimeWindow(since=NOW, until=NOW + timedelta(hours=1))

    assert window.contains(NOW)
    assert window.contains(NOW + timedelta(minutes=59))
    assert not window.contains(NOW + timedelta(hours=1))
    assert not window.contains(NOW - timedelta(seconds=1))


def test_a_window_without_bounds_holds_every_instant() -> None:
    assert TimeWindow().contains(datetime(2000, 1, 1, tzinfo=UTC))


# ADR indice-delle-previsioni-in-attesa-e-patrimonio-con-limite-superiore: an equity read always has an upper bound.
def test_a_window_without_an_end_ends_at_the_instant_given_holding_it() -> None:
    window = TimeWindow(since=NOW - timedelta(days=1)).ending_by(NOW)

    assert window.since == NOW - timedelta(days=1)
    assert window.until is not None
    assert window.contains(NOW)
    assert not window.contains(NOW + timedelta(microseconds=1))


def test_a_window_without_bounds_ending_by_now_keeps_no_start() -> None:
    window = TimeWindow().ending_by(NOW)

    assert window.since is None
    assert window.contains(datetime(2000, 1, 1, tzinfo=UTC))
    assert not window.contains(NOW + timedelta(seconds=1))


def test_a_window_with_its_own_end_keeps_it() -> None:
    window = TimeWindow(NOW - timedelta(hours=1), NOW + timedelta(minutes=1))

    assert window.ending_by(NOW) == window


# ADR periodo-al-minuto: truncation to the minute, the minute of the end included, an instant without a zone in UTC.
def test_the_window_of_minutes_truncates_both_instants_and_holds_the_minute_of_the_end() -> None:
    window = TimeWindow.of_minutes(
        datetime(2026, 11, 16, 9, 15, 59, 999999, tzinfo=UTC), datetime(2026, 11, 16, 11, 40, 1, tzinfo=UTC)
    )

    assert window == TimeWindow(
        since=datetime(2026, 11, 16, 9, 15, tzinfo=UTC), until=datetime(2026, 11, 16, 11, 41, tzinfo=UTC)
    )
    assert window.contains(datetime(2026, 11, 16, 11, 40, 59, tzinfo=UTC))
    assert not window.contains(datetime(2026, 11, 16, 11, 41, tzinfo=UTC))
    assert not window.contains(datetime(2026, 11, 16, 9, 14, 59, tzinfo=UTC))


def test_the_window_of_minutes_reads_an_instant_without_a_time_zone_in_utc() -> None:
    assert TimeWindow.of_minutes(datetime(2026, 11, 16, 9, 15), datetime(2026, 11, 16, 11, 40)) == TimeWindow(
        since=datetime(2026, 11, 16, 9, 15, tzinfo=UTC), until=datetime(2026, 11, 16, 11, 41, tzinfo=UTC)
    )


def test_the_window_of_minutes_moves_an_instant_of_another_time_zone_to_utc() -> None:
    rome = timezone(timedelta(hours=1))

    assert TimeWindow.of_minutes(datetime(2026, 11, 16, 10, 15, 30, tzinfo=rome), None) == TimeWindow(
        since=datetime(2026, 11, 16, 9, 15, tzinfo=UTC)
    )


def test_the_window_of_minutes_without_an_instant_has_no_bound_on_that_side() -> None:
    assert TimeWindow.of_minutes(None, datetime(2026, 11, 3, 8, 0, tzinfo=UTC)) == TimeWindow(
        until=datetime(2026, 11, 3, 8, 1, tzinfo=UTC)
    )
    assert TimeWindow.of_minutes(datetime(2026, 11, 1, 8, 0, tzinfo=UTC), None) == TimeWindow(
        since=datetime(2026, 11, 1, 8, 0, tzinfo=UTC)
    )
    assert TimeWindow.of_minutes(None, None) == TimeWindow()


def test_the_window_of_minutes_ending_before_it_starts_is_refused() -> None:
    with pytest.raises(InvalidStatisticsPeriodError):
        TimeWindow.of_minutes(datetime(2026, 11, 3, 8, 1, tzinfo=UTC), datetime(2026, 11, 3, 8, 0, 59, tzinfo=UTC))
