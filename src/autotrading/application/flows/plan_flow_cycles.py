from collections.abc import Callable
from functools import partial

from autotrading.application.flows.ports import (
    ClockPort,
    CycleJob,
    CycleSchedulerPort,
    PlannedFlowsPort,
    TenantScheduledFlow,
    TenantScheduledFlowsPort,
)
from autotrading.application.flows.run_cycle import RunCycleCommand, RunCycleUseCase
from autotrading.domain.tenancy.tenant_id import TenantId


class PlanFlowCyclesUseCase[S = object, D = object, C = object, A = object, O = object, E = object]:
    """Gives the scheduler one job per active flow, which runs the cycle planned at its instant (R1.2.1, R1.2.2).

    Called again and again by the worker, so a flow started, paused or changed meanwhile has its job added, dropped
    or replaced. A job run late or twice runs the latest planned instant not after now, and only once: an instant
    already taken by an executor is not run again. Each cycle runs on the ports of the tenant of its flow.
    """

    def __init__(
        self,
        flows: TenantScheduledFlowsPort,
        planned: PlannedFlowsPort,
        run_cycle_of: Callable[[TenantId], RunCycleUseCase[S, D, C, A, O, E]],
        scheduler: CycleSchedulerPort,
        clock: ClockPort,
    ) -> None:
        self._flows = flows
        self._planned = planned
        self._run_cycle_of = run_cycle_of
        self._scheduler = scheduler
        self._clock = clock

    def execute(self) -> None:
        entries = self._flows.active_of_every_tenant()
        self._planned.remember(entries)
        self._scheduler.keep([self._job_of(entry) for entry in entries])

    def _job_of(self, entry: TenantScheduledFlow) -> CycleJob:
        schedule = entry.flow.schedule
        key = f"{entry.tenant_id.value}/{entry.flow.flow_id}/{schedule.anchor.isoformat()}/{schedule.interval}"
        return CycleJob(key, schedule, partial(self._run_due_cycle, entry))

    def _run_due_cycle(self, entry: TenantScheduledFlow) -> None:
        planned_at = entry.flow.schedule.due_at(self._clock.now())
        if planned_at is None:
            return
        command = RunCycleCommand(entry.flow.flow_id, entry.flow.schedule, planned_at)
        self._run_cycle_of(entry.tenant_id).execute(command)
