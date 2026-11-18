from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.errors import CycleInProgressError, FlowNotActiveError
from autotrading.application.flows.ports import ClockPort, FlowRepositoryPort, FlowTimingPort
from autotrading.application.flows.run_cycle import RunCycleCommand
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_timing import UNSTAMPED

# The run of RunCycleUseCase on the graph of the tenant of the flow, whatever the types its nodes hand one another.
type CycleRun = Callable[[RunCycleCommand], CycleRecord | None]


@dataclass(frozen=True, slots=True)
class RunCycleOnDemandCommand:
    flow_id: UUID


class RunCycleOnDemandUseCase:
    """Runs a cycle of an active flow now, the same full cycle as the planned ones (R6.5.2, ADR
    ciclo-su-richiesta-nel-worker).

    The cycle keeps the schedule of the flow, so the next planned cycle stays at its instant, and is planned at the
    instant the user asks for it. An instant another executor already took is a cycle in progress.
    """

    def __init__(
        self, flows: FlowRepositoryPort, timing: FlowTimingPort, clock: ClockPort, run_cycle: CycleRun
    ) -> None:
        self._flows = flows
        self._timing = timing
        self._clock = clock
        self._run_cycle = run_cycle

    def execute(self, command: RunCycleOnDemandCommand) -> CycleRecord:
        schedule = self._schedule_of(FlowId(command.flow_id))
        record = self._run_cycle(RunCycleCommand(command.flow_id, schedule, self._clock.now(), CycleTrigger.ON_DEMAND))
        if record is None:
            raise CycleInProgressError
        return record

    def _schedule_of(self, flow_id: FlowId) -> CycleSchedule:
        """The schedule of the flow as the planner reads it: from its last start or resume, every interval."""
        flow = self._flows.get(flow_id)
        anchor = self._timing.timings().get(flow_id, UNSTAMPED).anchor
        schedule = flow.planned_schedule(anchor)
        if schedule is None:
            raise FlowNotActiveError
        return schedule
