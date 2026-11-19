from datetime import timedelta

import pytest

from autotrading.domain.flows.cycle_interval import DEFAULT_CYCLE_INTERVAL, CycleInterval
from autotrading.domain.flows.errors import CycleIntervalOutOfRangeError


@pytest.mark.parametrize("minutes", [0, 1441])
def test_an_interval_outside_a_minute_and_a_day_is_refused(minutes: int) -> None:
    with pytest.raises(CycleIntervalOutOfRangeError):
        CycleInterval(minutes)


def test_a_flow_that_names_no_interval_runs_a_cycle_every_15_minutes() -> None:
    assert CycleInterval.of(None) == DEFAULT_CYCLE_INTERVAL == CycleInterval(15)


def test_the_interval_named_is_kept() -> None:
    assert CycleInterval.of(60) == CycleInterval(60)


@pytest.mark.parametrize(
    ("minutes", "wait"), [(1, timedelta(seconds=15)), (15, timedelta(seconds=60)), (1440, timedelta(seconds=60))]
)
def test_a_cycle_waits_for_a_source_a_quarter_of_its_interval_and_never_more_than_a_minute(
    minutes: int, wait: timedelta
) -> None:
    assert CycleInterval(minutes).source_wait == wait


def test_a_trial_waits_for_a_source_as_the_cycles_of_the_default_interval() -> None:
    assert DEFAULT_CYCLE_INTERVAL.source_wait == timedelta(seconds=60)
