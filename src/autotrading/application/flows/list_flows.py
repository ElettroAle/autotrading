from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow import Flow


class ListFlowsUseCase:
    """The flows of the tenant, each with the configuration version in force (R1.1.1)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self) -> list[Flow]:
        return sorted(self._flows.list(), key=lambda flow: flow.name.value)
