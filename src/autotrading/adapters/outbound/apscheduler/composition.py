from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

from autotrading.adapters.outbound.apscheduler.configuration import _ApSchedulerSettings
from autotrading.adapters.outbound.apscheduler.cycle_scheduler import ApSchedulerCycleSchedulerAdapter


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
