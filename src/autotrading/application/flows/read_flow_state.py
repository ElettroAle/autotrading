from dataclasses import dataclass

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.ports import AccountActivityPort, FlowRepositoryPort, PlatformOrdersPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState


def find_flow(flows: FlowRepositoryPort, flow_id: FlowId) -> Flow:
    flow = next((flow for flow in flows.list() if flow.id == flow_id), None)
    if flow is None:
        raise FlowNotFoundError
    return flow


@dataclass(frozen=True, slots=True)
class ReadFlowStateCommand:
    flow_id: FlowId


class ReadFlowStateUseCase:
    """The state of a flow attributed from what the exchange shows of its account now (R1.6.1)."""

    def __init__(self, flows: FlowRepositoryPort, activity: AccountActivityPort, orders: PlatformOrdersPort) -> None:
        self._flows = flows
        self._activity = activity
        self._orders = orders

    def execute(self, command: ReadFlowStateCommand) -> FlowState:
        flow = find_flow(self._flows, command.flow_id)
        activity = self._activity.activity(flow.account_id)
        orders = self._orders.orders_of_account(flow.account_id)
        orders_of_flow = frozenset(order for order, owner in orders.items() if owner == flow.id)
        return FlowState.attributed(flow, activity, orders_of_flow)
