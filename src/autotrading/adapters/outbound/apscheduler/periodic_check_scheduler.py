import logging
from collections.abc import Callable
from datetime import UTC, timedelta

from apscheduler.triggers.interval import IntervalTrigger

from autotrading.adapters.outbound.apscheduler.check_scheduler import _CheckScheduler


class ApSchedulerPeriodicCheckSchedulerAdapter(_CheckScheduler):
    """One APScheduler job per periodic check of the worker, at once and then at every interval (ADR
    sorveglianza-del-prezzo-per-lo-stop-che-segue): an interval, unlike the instants of a cycle, has no anchor to keep,
    and the next interval tries again after an error.
    """

    _operations = logging.getLogger("autotrading.flows")
    _warning = "controllo periodico interrotto"

    def keep_every(self, name: str, every: timedelta, run: Callable[[], None]) -> None:
        self._keep(name, IntervalTrigger(seconds=every.total_seconds(), timezone=UTC), run)
