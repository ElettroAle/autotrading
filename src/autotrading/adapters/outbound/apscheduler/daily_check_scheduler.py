import logging
from collections.abc import Callable
from datetime import UTC, datetime, time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from autotrading.domain.errors import AutotradingError

operations = logging.getLogger("autotrading.notifications")


class ApSchedulerDailyCheckSchedulerAdapter:
    """One APScheduler job per daily check of the worker, at once and then every day at its instant (ADR
    controllo-giornaliero-delle-scadenze).

    Kept again under the same name, the job is replaced, never doubled. The error of the project a check still raises
    is logged here and never reaches the scheduler: the next day tries again.
    """

    def __init__(self, scheduler: BackgroundScheduler) -> None:
        self._scheduler = scheduler

    def keep_daily(self, name: str, at: time, run: Callable[[], None]) -> None:
        trigger = CronTrigger(hour=at.hour, minute=at.minute, timezone=at.tzinfo or UTC)
        self._scheduler.add_job(
            _run, trigger, args=(name, run), id=name, replace_existing=True, next_run_time=datetime.now(UTC)
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
        operations.warning("controllo giornaliero interrotto", extra={"check": name, "error": str(error)})
