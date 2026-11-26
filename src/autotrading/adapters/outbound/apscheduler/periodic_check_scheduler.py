import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from autotrading.domain.errors import AutotradingError

operations = logging.getLogger("autotrading.flows")


class ApSchedulerPeriodicCheckSchedulerAdapter:
    """One APScheduler job per periodic check of the worker, at once and then at every interval (ADR
    sorveglianza-del-prezzo-per-lo-stop-che-segue).

    An interval, unlike the instants of a cycle, has no anchor to keep. Kept again under the same name, the job is
    replaced, never doubled. The error of the project a check still raises is logged here and never reaches the
    scheduler: the next interval tries again.
    """

    def __init__(self, scheduler: BackgroundScheduler) -> None:
        self._scheduler = scheduler

    def keep_every(self, name: str, every: timedelta, run: Callable[[], None]) -> None:
        self._scheduler.add_job(
            _run,
            IntervalTrigger(seconds=every.total_seconds(), timezone=UTC),
            args=(name, run),
            id=name,
            replace_existing=True,
            next_run_time=datetime.now(UTC),
        )
        if not self._scheduler.running:
            self._scheduler.start()

    def next_instants(self) -> dict[str, datetime]:
        """The next run of every check, by name."""
        return {planned.id: planned.next_run_time for planned in self._scheduler.get_jobs()}

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)


def _run(name: str, check: Callable[[], None]) -> None:
    try:
        check()
    except AutotradingError as error:
        operations.warning("controllo periodico interrotto", extra={"check": name, "error": str(error)})
