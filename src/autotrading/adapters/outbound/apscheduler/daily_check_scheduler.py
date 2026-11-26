import logging
from collections.abc import Callable
from datetime import UTC, time

from apscheduler.triggers.cron import CronTrigger

from autotrading.adapters.outbound.apscheduler.check_scheduler import _CheckScheduler


class ApSchedulerDailyCheckSchedulerAdapter(_CheckScheduler):
    """One APScheduler job per daily check of the worker, at once and then every day at its instant (ADR
    controllo-giornaliero-delle-scadenze): the next day tries again after an error.
    """

    _operations = logging.getLogger("autotrading.notifications")
    _warning = "controllo giornaliero interrotto"

    def keep_daily(self, name: str, at: time, run: Callable[[], None]) -> None:
        self._keep(name, CronTrigger(hour=at.hour, minute=at.minute, timezone=at.tzinfo or UTC), run)
