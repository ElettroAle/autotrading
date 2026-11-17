from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import FlowRepositoryPort, OpeningsSuspensionPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_suspension import OpeningsStatus


@dataclass(frozen=True, slots=True)
class ResumeFlowOpeningsCommand:
    flow_id: FlowId


class ResumeFlowOpeningsUseCase:
    """The user resumes the openings of a flow suspended for maximum loss, with either resume, also before the next day
    (R3.2.2). The peak counts again from now; openings not suspended are refused.
    """

    def __init__(
        self, flows: FlowRepositoryPort, openings: OpeningsSuspensionPort, clock: Callable[[], datetime]
    ) -> None:
        self._flows = flows
        self._openings = openings
        self._clock = clock

    def execute(self, command: ResumeFlowOpeningsCommand) -> OpeningsStatus:
        flow = self._flows.get(command.flow_id)
        now = self._clock()
        status = self._openings.status(flow.id.value).at(now, flow.configuration.openings_resume)
        resumed = status.resumed(now, flow.name.value)
        self._openings.resume(flow.id.value, now)
        return resumed
