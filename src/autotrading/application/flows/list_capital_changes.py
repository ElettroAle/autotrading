from dataclasses import dataclass

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class ListCapitalChangesCommand:
    flow_id: FlowId


class ListCapitalChangesUseCase:
    """The history of the capital allocated to a flow, oldest change first (R1.1.7)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: ListCapitalChangesCommand) -> tuple[CapitalChange, ...]:
        return self._flows.capital_changes(command.flow_id)
