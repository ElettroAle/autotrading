import logging
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, time, timedelta

import pytest

from autotrading.adapters.outbound.apscheduler.composition import apscheduler_daily_check_adapters
from autotrading.adapters.outbound.apscheduler.daily_check_scheduler import ApSchedulerDailyCheckSchedulerAdapter
from autotrading.domain.errors import AutotradingError

WAITING = 5.0
SIX = time(6, 0, tzinfo=UTC)


class UnreachableExampleError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("database non raggiungibile")


@pytest.fixture
def scheduler() -> Iterator[ApSchedulerDailyCheckSchedulerAdapter]:
    adapter = apscheduler_daily_check_adapters()
    yield adapter
    adapter.stop()


def test_a_check_runs_at_once_and_then_every_day_at_its_instant(
    scheduler: ApSchedulerDailyCheckSchedulerAdapter,
) -> None:
    ran = threading.Event()

    scheduler.keep_daily("scadenze", SIX, ran.set)

    assert ran.wait(WAITING)
    following = scheduler.next_instants()["scadenze"]
    assert (following.hour, following.minute, following.utcoffset()) == (6, 0, timedelta(0))
    assert following - datetime.now(UTC) <= timedelta(days=1)


def test_a_check_kept_again_replaces_the_one_kept_before(scheduler: ApSchedulerDailyCheckSchedulerAdapter) -> None:
    first, second = threading.Event(), threading.Event()

    scheduler.keep_daily("scadenze", SIX, first.set)
    scheduler.keep_daily("scadenze", SIX, second.set)

    assert second.wait(WAITING)
    assert list(scheduler.next_instants()) == ["scadenze"]


def test_an_error_of_the_project_is_logged_and_never_reaches_the_scheduler(
    scheduler: ApSchedulerDailyCheckSchedulerAdapter, caplog: pytest.LogCaptureFixture
) -> None:
    failed = threading.Event()

    def check() -> None:
        failed.set()
        raise UnreachableExampleError

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        scheduler.keep_daily("scadenze", SIX, check)
        assert failed.wait(WAITING)
        assert _logged(caplog)

    assert "scadenze" in scheduler.next_instants()


def _logged(caplog: pytest.LogCaptureFixture) -> bool:
    deadline = datetime.now(UTC) + timedelta(seconds=WAITING)
    while datetime.now(UTC) < deadline:
        if any(record.getMessage() == "controllo giornaliero interrotto" for record in caplog.records):
            return True
        threading.Event().wait(0.01)
    return False


def test_stopping_a_scheduler_never_started_does_nothing() -> None:
    apscheduler_daily_check_adapters().stop()
