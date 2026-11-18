from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import FlowRepositoryPort, FlowTimingPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_timing import UNSTAMPED


@dataclass(frozen=True, slots=True)
class ReadNextCycleCommand:
    flow_id: FlowId


class ReadNextCycleUseCase:
    """The first planned cycle of a flow of the tenant after now, the same instant the list of the flows shows (R2.2.2,
    R6.4.8, ADR prossima-esecuzione-nel-riepilogo-del-flusso); None for a flow that plans no cycle.
    """

    def __init__(self, flows: FlowRepositoryPort, timing: FlowTimingPort, clock: Callable[[], datetime]) -> None:
        self._flows = flows
        self._timing = timing
        self._clock = clock

    def execute(self, command: ReadNextCycleCommand) -> datetime | None:
        flow = self._flows.get(command.flow_id)
        schedule = flow.planned_schedule(self._timing.timings().get(flow.id, UNSTAMPED).anchor)
        return None if schedule is None else schedule.next_after(self._clock())
