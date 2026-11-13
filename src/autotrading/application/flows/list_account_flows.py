from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow import Flow


@dataclass(frozen=True, slots=True)
class ListAccountFlowsCommand:
    account_id: UUID


class ListAccountFlowsUseCase:
    """The flows of the tenant that run on an account, active or paused (R1.1.8)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: ListAccountFlowsCommand) -> list[Flow]:
        return [flow for flow in self._flows.list() if flow.runs_on(command.account_id)]
