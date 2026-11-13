import logging
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.base import BaseTrigger

from autotrading.application.flows.ports import CycleJob
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_schedule import CycleSchedule

operations = logging.getLogger("autotrading.cycles")


class ApSchedulerCycleSchedulerAdapter:
    """One APScheduler job per active flow, at the instants of its schedule (docs/architecture.md:144, ADR 0112).

    A new job runs once at once, then at every planned instant after that: its first cycle takes the instant due
    now, if no executor took it yet. Every run is in a thread of the pool, so a slow flow never delays another; the
    error a cycle still raises, a permanent one, is logged here and never reaches the scheduler.
    """

    def __init__(self, scheduler: BackgroundScheduler) -> None:
        self._scheduler = scheduler

    def keep(self, jobs: Sequence[CycleJob]) -> None:
        wanted = {job.key: job for job in jobs}
        self._drop_all_but(wanted.keys())
        known = {planned.id for planned in self._scheduler.get_jobs()}
        for job in wanted.values():
            if job.key not in known:
                self._scheduler.add_job(_run, _CycleTrigger(job.schedule), args=(job.run,), id=job.key)
        if not self._scheduler.running:
            self._scheduler.start()

    def next_instants(self) -> dict[str, datetime]:
        """The next run of every job, by key."""
        return {planned.id: planned.next_run_time for planned in self._scheduler.get_jobs()}

    def stop(self) -> None:
        """Lets the running cycles finish and starts no other."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)

    def _drop_all_but(self, keys: Iterable[str]) -> None:
        kept = set(keys)
        for planned in self._scheduler.get_jobs():
            if planned.id not in kept:
                planned.remove()


# APScheduler 3 ships no types, and add_job takes only a subclass of its BaseTrigger.
class _CycleTrigger(BaseTrigger):  # type: ignore[misc]
    """At once when the job is added, then at every planned instant of the schedule, never drifting from its anchor."""

    def __init__(self, schedule: CycleSchedule) -> None:
        self._schedule = schedule

    def get_next_fire_time(self, previous_fire_time: datetime | None, now: datetime) -> datetime:
        if previous_fire_time is None:
            return now
        return self._schedule.next_after(previous_fire_time)


def _run(task: Callable[[], object]) -> None:
    try:
        task()
    except AutotradingError as error:
        operations.warning("ciclo interrotto da un errore permanente", extra={"error": str(error)})
