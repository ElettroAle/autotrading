from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

from autotrading.adapters.outbound.apscheduler.configuration import _ApSchedulerSettings
from autotrading.adapters.outbound.apscheduler.cycle_scheduler import ApSchedulerCycleSchedulerAdapter
from autotrading.adapters.outbound.apscheduler.daily_check_scheduler import ApSchedulerDailyCheckSchedulerAdapter
from autotrading.adapters.outbound.apscheduler.periodic_check_scheduler import ApSchedulerPeriodicCheckSchedulerAdapter


def apscheduler_adapters() -> ApSchedulerCycleSchedulerAdapter:
    """The scheduler of the cycles, started by the first jobs it is given (ADR 0112)."""
    settings = _ApSchedulerSettings()
    scheduler = BackgroundScheduler(
        executors={"default": ThreadPoolExecutor(settings.threads)},
        job_defaults={
            # A run woken late still runs, once: its cycle takes the latest instant due (ADR 0041).
            "coalesce": True,
            "misfire_grace_time": None,
            "max_instances": settings.running_per_flow,
        },
        timezone=settings.zone,
    )
    return ApSchedulerCycleSchedulerAdapter(scheduler)


def apscheduler_daily_check_adapters() -> ApSchedulerDailyCheckSchedulerAdapter:
    """The scheduler of the daily checks of the worker, one thread: a check never runs beside itself (ADR
    controllo-giornaliero-delle-scadenze)."""
    settings = _ApSchedulerSettings()
    scheduler = BackgroundScheduler(
        executors={"default": ThreadPoolExecutor(settings.daily_check_threads)},
        # A check woken late still runs, once.
        job_defaults={"coalesce": True, "misfire_grace_time": None, "max_instances": 1},
        timezone=settings.zone,
    )
    return ApSchedulerDailyCheckSchedulerAdapter(scheduler)


def apscheduler_periodic_check_adapters() -> ApSchedulerPeriodicCheckSchedulerAdapter:
    """The scheduler of the periodic checks of the worker, one thread: a check never runs beside itself (ADR
    sorveglianza-del-prezzo-per-lo-stop-che-segue)."""
    settings = _ApSchedulerSettings()
    scheduler = BackgroundScheduler(
        executors={"default": ThreadPoolExecutor(settings.periodic_check_threads)},
        # A check woken late runs once: the prices of now are the ones that count.
        job_defaults={"coalesce": True, "misfire_grace_time": None, "max_instances": 1},
        timezone=settings.zone,
    )
    return ApSchedulerPeriodicCheckSchedulerAdapter(scheduler)
