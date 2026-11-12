from datetime import UTC, datetime, timedelta

import pytest

from autotrading.domain.cycles.cycle_schedule import CycleSchedule, delay_seconds
from autotrading.domain.cycles.errors import InvalidScheduleError

ANCHOR = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
QUARTER = timedelta(minutes=15)


def minutes_after_anchor(minutes: float) -> datetime:
    return ANCHOR + timedelta(minutes=minutes)


def test_an_anchor_without_time_zone_is_refused() -> None:
    with pytest.raises(InvalidScheduleError, match="pianificazione dei cicli non valida"):
        CycleSchedule(datetime(2026, 11, 12, 10, 7), QUARTER)


@pytest.mark.parametrize("interval", [timedelta(0), timedelta(minutes=-1)])
def test_an_interval_that_is_not_positive_is_refused(interval: timedelta) -> None:
    with pytest.raises(InvalidScheduleError):
        CycleSchedule(ANCHOR, interval)


def test_the_invalid_schedule_is_a_defect() -> None:
    assert InvalidScheduleError().status_code == 500


def test_no_cycle_is_due_before_the_anchor() -> None:
    assert CycleSchedule(ANCHOR, QUARTER).due_at(minutes_after_anchor(-1)) is None


@pytest.mark.parametrize(("minutes", "due"), [(0, 0), (14.99, 0), (15, 15), (16, 15), (31, 30)])
def test_the_due_cycle_is_the_latest_planned_instant_not_after_now(minutes: float, due: int) -> None:
    assert CycleSchedule(ANCHOR, QUARTER).due_at(minutes_after_anchor(minutes)) == minutes_after_anchor(due)


def test_before_the_anchor_the_next_cycle_is_the_anchor() -> None:
    assert CycleSchedule(ANCHOR, QUARTER).next_after(minutes_after_anchor(-5)) == ANCHOR


@pytest.mark.parametrize(("minutes", "following"), [(0, 15), (1, 15), (15, 30), (29, 30)])
def test_the_next_cycle_is_the_first_planned_instant_after_now(minutes: float, following: int) -> None:
    assert CycleSchedule(ANCHOR, QUARTER).next_after(minutes_after_anchor(minutes)) == minutes_after_anchor(following)


@pytest.mark.parametrize(
    ("interval", "wait"),
    [
        (timedelta(minutes=2), timedelta(seconds=30)),
        (timedelta(minutes=4), timedelta(seconds=60)),
        (timedelta(minutes=15), timedelta(seconds=60)),
    ],
)
def test_sources_wait_a_quarter_of_the_interval_and_never_beyond_a_minute(interval: timedelta, wait: timedelta) -> None:
    assert CycleSchedule(ANCHOR, interval).source_wait == wait


@pytest.mark.parametrize(("seconds", "delay"), [(0, None), (40, None), (60, None), (61, 61), (90, 90)])
def test_a_cycle_is_late_only_beyond_a_minute(seconds: int, delay: int | None) -> None:
    assert delay_seconds(ANCHOR, ANCHOR + timedelta(seconds=seconds)) == delay
