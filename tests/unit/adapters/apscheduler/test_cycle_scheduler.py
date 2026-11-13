import logging
import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest

from autotrading.adapters.outbound.apscheduler.composition import apscheduler_adapters
from autotrading.adapters.outbound.apscheduler.cycle_scheduler import ApSchedulerCycleSchedulerAdapter
from autotrading.application.flows.ports import CycleJob
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_schedule import CycleSchedule

WAITING = 5.0
# Long enough that a job planned at the next instant never runs during the test.
LATER = timedelta(hours=1)


class PermanentExampleError(AutotradingError):
    permanent = True

    def __init__(self) -> None:
        super().__init__("credito esaurito presso openrouter")


class Runs:
    """Counts the runs of a job and lets the test wait for the next one."""

    def __init__(self, body: Callable[[], object] = lambda: None) -> None:
        self.count = 0
        self._body = body
        self._ran = threading.Condition()

    def __call__(self) -> None:
        with self._ran:
            self.count += 1
            self._ran.notify_all()
        self._body()

    def wait_for(self, count: int) -> bool:
        with self._ran:
            return self._ran.wait_for(lambda: self.count >= count, WAITING)


def eventually(condition: Callable[[], bool]) -> bool:
    deadline = time.monotonic() + WAITING
    while not condition():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


@pytest.fixture
def scheduler() -> Iterator[ApSchedulerCycleSchedulerAdapter]:
    adapter = apscheduler_adapters()
    yield adapter
    adapter.stop()


def job(key: str, run: Callable[[], object], interval: timedelta = LATER, anchor: datetime | None = None) -> CycleJob:
    return CycleJob(key, CycleSchedule(anchor or datetime.now(UTC) - timedelta(minutes=7), interval), run)


def test_a_new_job_runs_at_once(scheduler: ApSchedulerCycleSchedulerAdapter) -> None:
    runs = Runs()

    scheduler.keep([job("alfa", runs)])

    assert runs.wait_for(1)


def test_a_job_runs_again_at_the_instants_of_its_schedule(scheduler: ApSchedulerCycleSchedulerAdapter) -> None:
    runs = Runs()

    scheduler.keep([job("alfa", runs, interval=timedelta(milliseconds=200), anchor=datetime.now(UTC))])

    assert runs.wait_for(3)


def test_the_instants_follow_the_anchor_not_the_moment_the_job_is_added(
    scheduler: ApSchedulerCycleSchedulerAdapter,
) -> None:
    anchor, runs = datetime.now(UTC) - timedelta(minutes=7), Runs()

    scheduler.keep([job("alfa", runs, interval=timedelta(minutes=15), anchor=anchor)])

    assert runs.wait_for(1)
    assert eventually(lambda: scheduler.next_instants() == {"alfa": anchor + timedelta(minutes=15)})


def test_a_job_kept_again_is_not_run_again_at_once(scheduler: ApSchedulerCycleSchedulerAdapter) -> None:
    runs, later = Runs(), Runs()
    scheduler.keep([job("alfa", runs)])
    assert runs.wait_for(1)

    scheduler.keep([job("alfa", runs), job("beta", later)])

    assert later.wait_for(1)
    assert runs.count == 1


def test_a_job_not_given_any_more_is_dropped(scheduler: ApSchedulerCycleSchedulerAdapter) -> None:
    scheduler.keep([job("alfa", Runs()), job("beta", Runs())])

    scheduler.keep([job("beta", Runs())])

    assert set(scheduler.next_instants()) == {"beta"}


def test_a_slow_job_does_not_hold_another(scheduler: ApSchedulerCycleSchedulerAdapter) -> None:
    release = threading.Event()
    slow, quick = Runs(lambda: release.wait(WAITING)), Runs()

    scheduler.keep([job("alfa", slow), job("beta", quick)])

    assert quick.wait_for(1)
    release.set()


def test_an_instant_still_running_its_previous_cycle_still_starts(scheduler: ApSchedulerCycleSchedulerAdapter) -> None:
    release = threading.Event()
    held = Runs(lambda: release.wait(WAITING))

    scheduler.keep([job("alfa", held, interval=timedelta(milliseconds=200), anchor=datetime.now(UTC))])

    # The cycle itself finds its flow held and records the instant as skipped (R1.2.2).
    assert held.wait_for(2)
    release.set()


def test_an_error_out_of_the_cycle_is_logged_and_never_raised(
    scheduler: ApSchedulerCycleSchedulerAdapter, caplog: pytest.LogCaptureFixture
) -> None:
    def failing() -> None:
        raise PermanentExampleError

    runs = Runs(failing)
    with caplog.at_level(logging.WARNING, logger="autotrading.cycles"):
        scheduler.keep([job("alfa", runs)])
        assert runs.wait_for(1)
        scheduler.stop()

    [entry] = [record for record in caplog.records if record.name == "autotrading.cycles"]
    assert entry.getMessage() == "ciclo interrotto da un errore permanente"
    assert entry.__dict__["error"] == "credito esaurito presso openrouter"
