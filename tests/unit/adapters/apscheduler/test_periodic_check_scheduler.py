"""The periodic checks of the worker on APScheduler (R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

import logging
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from autotrading.adapters.outbound.apscheduler.composition import apscheduler_periodic_check_adapters
from autotrading.adapters.outbound.apscheduler.periodic_check_scheduler import ApSchedulerPeriodicCheckSchedulerAdapter
from autotrading.domain.errors import AutotradingError

WAITING = 5.0
SHORT = timedelta(milliseconds=50)


class UnreachableExampleError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("database non raggiungibile")


@pytest.fixture
def scheduler() -> Iterator[ApSchedulerPeriodicCheckSchedulerAdapter]:
    adapter = apscheduler_periodic_check_adapters()
    yield adapter
    adapter.stop()


def test_a_check_runs_at_once_and_then_at_every_interval(scheduler: ApSchedulerPeriodicCheckSchedulerAdapter) -> None:
    runs: list[datetime] = []
    again = threading.Event()

    def check() -> None:
        runs.append(datetime.now(UTC))
        if len(runs) > 1:
            again.set()

    scheduler.keep_every("stop", SHORT, check)

    assert again.wait(WAITING)


def test_the_next_run_is_one_interval_away() -> None:
    adapter = apscheduler_periodic_check_adapters()
    try:
        adapter.keep_every("stop", timedelta(minutes=1), lambda: None)
        following = adapter.next_instants()["stop"]
        assert following - datetime.now(UTC) <= timedelta(minutes=1)
    finally:
        adapter.stop()


def test_a_check_kept_again_replaces_the_one_kept_before(scheduler: ApSchedulerPeriodicCheckSchedulerAdapter) -> None:
    first, second = threading.Event(), threading.Event()

    scheduler.keep_every("stop", timedelta(minutes=1), first.set)
    scheduler.keep_every("stop", timedelta(minutes=1), second.set)

    assert second.wait(WAITING)
    assert list(scheduler.next_instants()) == ["stop"]


def test_an_error_of_the_project_is_logged_and_never_reaches_the_scheduler(
    scheduler: ApSchedulerPeriodicCheckSchedulerAdapter, caplog: pytest.LogCaptureFixture
) -> None:
    failed = threading.Event()

    def check() -> None:
        failed.set()
        raise UnreachableExampleError

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        scheduler.keep_every("stop", timedelta(minutes=1), check)
        assert failed.wait(WAITING)
        assert _logged(caplog)

    assert "stop" in scheduler.next_instants()


def _logged(caplog: pytest.LogCaptureFixture) -> bool:
    deadline = datetime.now(UTC) + timedelta(seconds=WAITING)
    while datetime.now(UTC) < deadline:
        if any(record.getMessage() == "controllo periodico interrotto" for record in caplog.records):
            return True
        threading.Event().wait(0.01)
    return False


def test_stopping_a_scheduler_never_started_does_nothing() -> None:
    apscheduler_periodic_check_adapters().stop()
