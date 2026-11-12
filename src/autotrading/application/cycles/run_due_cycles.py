from functools import partial

from autotrading.application.cycles.ports import ClockPort, CycleLauncherPort, ScheduledFlowsPort
from autotrading.application.cycles.run_cycle import RunCycleCommand, RunCycleUseCase


class RunDueCyclesUseCase:
    """Launches, for every active flow, the cycle planned at the latest instant not after now (R1.2.1, R1.2.2).

    Called again and again by the worker: a planned instant already taken by an executor is not run twice.
    """

    def __init__(
        self, flows: ScheduledFlowsPort, run_cycle: RunCycleUseCase, launcher: CycleLauncherPort, clock: ClockPort
    ) -> None:
        self._flows = flows
        self._run_cycle = run_cycle
        self._launcher = launcher
        self._clock = clock

    def execute(self) -> None:
        now = self._clock.now()
        for flow in self._flows.active():
            planned_at = flow.schedule.due_at(now)
            if planned_at is None:
                continue
            command = RunCycleCommand(flow.flow_id, flow.schedule, planned_at)
            self._launcher.launch(partial(self._run_cycle.execute, command))
