import logging
from collections.abc import Callable
from datetime import UTC, datetime, tzinfo
from typing import ClassVar

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.base import BaseTrigger

from autotrading.domain.errors import AutotradingError


def _check_background_scheduler(threads: int, zone: tzinfo) -> BackgroundScheduler:
    """The scheduler of the checks of the worker: a check woken late runs once, and never beside itself."""
    return BackgroundScheduler(
        executors={"default": ThreadPoolExecutor(threads)},
        job_defaults={"coalesce": True, "misfire_grace_time": None, "max_instances": 1},
        timezone=zone,
    )


class _CheckScheduler:
    """What every scheduler of the checks of the worker shares: one job per check, run at once and then by its trigger;
    kept again under the same name, the job is replaced, never doubled. The error of the project a check still raises is
    logged with the logger and the warning of the scheduler, and never reaches it: the next run tries again.
    """

    _operations: ClassVar[logging.Logger]
    _warning: ClassVar[str]

    def __init__(self, scheduler: BackgroundScheduler) -> None:
        self._scheduler = scheduler

    def next_instants(self) -> dict[str, datetime]:
        """The next run of every check, by name."""
        return {planned.id: planned.next_run_time for planned in self._scheduler.get_jobs()}

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)

    def _keep(self, name: str, trigger: BaseTrigger, run: Callable[[], None]) -> None:
        self._scheduler.add_job(
            _run_check,
            trigger,
            args=(name, run, self._operations, self._warning),
            id=name,
            replace_existing=True,
            next_run_time=datetime.now(UTC),
        )
        if not self._scheduler.running:
            self._scheduler.start()


def _run_check(name: str, check: Callable[[], None], operations: logging.Logger, warning: str) -> None:
    try:
        check()
    except AutotradingError as error:
        operations.warning(warning, extra={"check": name, "error": str(error)})
