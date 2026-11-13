from collections.abc import Callable
from functools import partial

from autotrading.application.flows.ports import (
    ClockPort,
    CycleLauncherPort,
    PlannedFlowsPort,
    TenantScheduledFlowsPort,
)
from autotrading.application.flows.run_cycle import RunCycleCommand, RunCycleUseCase
from autotrading.domain.tenancy.tenant_id import TenantId


class RunDueCyclesUseCase[S = object, D = object, C = object, A = object, O = object, E = object]:
    """Launches, for every active flow, the cycle planned at the latest instant not after now (R1.2.1, R1.2.2).

    Called again and again by the worker: a planned instant already taken by an executor is not run twice. Each
    cycle runs on the ports of the tenant of its flow.
    """

    def __init__(
        self,
        flows: TenantScheduledFlowsPort,
        planned: PlannedFlowsPort,
        run_cycle_of: Callable[[TenantId], RunCycleUseCase[S, D, C, A, O, E]],
        launcher: CycleLauncherPort,
        clock: ClockPort,
    ) -> None:
        self._flows = flows
        self._planned = planned
        self._run_cycle_of = run_cycle_of
        self._launcher = launcher
        self._clock = clock

    def execute(self) -> None:
        now = self._clock.now()
        entries = self._flows.active_of_every_tenant()
        self._planned.remember(entries)
        for entry in entries:
            planned_at = entry.flow.schedule.due_at(now)
            if planned_at is None:
                continue
            command = RunCycleCommand(entry.flow.flow_id, entry.flow.schedule, planned_at)
            self._launcher.launch(partial(self._run_cycle_of(entry.tenant_id).execute, command))
