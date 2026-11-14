from dataclasses import dataclass

from autotrading.application.flows.ports import FlowRepositoryPort, FlowVersion
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class ListFlowVersionsCommand:
    flow_id: FlowId


class ListFlowVersionsUseCase:
    """The configuration versions of a flow with when each was saved, newest first (R2.3.5, ADR 0133)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: ListFlowVersionsCommand) -> tuple[FlowVersion, ...]:
        return self._flows.versions(command.flow_id)
