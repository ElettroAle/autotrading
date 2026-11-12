from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus


class ListFlowsUseCase:
    """The flows in use of the tenant, or the archived ones, each with the configuration version in force (R1.1.6)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, *, archived: bool = False) -> list[Flow]:
        listed = (flow for flow in self._flows.list() if (flow.status == FlowStatus.ARCHIVED) == archived)
        return sorted(listed, key=lambda flow: flow.name.value)
