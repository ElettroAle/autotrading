from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import FlowRepositoryPort, OpeningsSuspensionPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_suspension import OpeningsSuspension


@dataclass(frozen=True, slots=True)
class ReadFlowOpeningsCommand:
    flow_id: FlowId


class ReadFlowOpeningsUseCase:
    """The suspension of the openings of a flow of the tenant in force now, or None (R3.2.2).

    A suspension the next day reads lifted from its midnight, before any cycle writes it.
    """

    def __init__(
        self, flows: FlowRepositoryPort, openings: OpeningsSuspensionPort, clock: Callable[[], datetime]
    ) -> None:
        self._flows = flows
        self._openings = openings
        self._clock = clock

    def execute(self, command: ReadFlowOpeningsCommand) -> OpeningsSuspension | None:
        flow = self._flows.get(command.flow_id)
        return self._openings.status(flow.id.value).at(self._clock(), flow.configuration.openings_resume).suspension
