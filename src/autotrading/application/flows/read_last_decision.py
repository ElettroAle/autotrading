from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.ports import CycleHistoryPort, FlowDirectoryPort
from autotrading.domain.flows.recorded_decision import DecidedCycle


@dataclass(frozen=True, slots=True)
class ReadLastDecisionCommand:
    flow_id: UUID


class ReadLastDecisionUseCase:
    """The last decision of the agent in a flow of the tenant: the decisions of its most recent completed cycle that
    has any, whatever the period the user looks at; None before the first (R6.5.4).
    """

    def __init__(self, flows: FlowDirectoryPort, history: CycleHistoryPort) -> None:
        self._flows = flows
        self._history = history

    def execute(self, command: ReadLastDecisionCommand) -> DecidedCycle | None:
        if not self._flows.exists(command.flow_id):
            raise CycleFlowNotFoundError
        return self._history.last_decided(command.flow_id)
