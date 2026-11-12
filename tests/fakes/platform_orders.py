"""Fake of the orders the platform sent: client order id, account and the flow that sent it, if any."""

from uuid import UUID

from autotrading.domain.flows.account_reconciliation import PlatformOrders
from autotrading.domain.flows.flow_id import FlowId


class InMemoryPlatformOrdersAdapter:
    def __init__(self) -> None:
        self.orders: dict[UUID, tuple[UUID, FlowId | None]] = {}

    def add(self, order_id: UUID, account_id: UUID, flow_id: FlowId | None) -> None:
        self.orders[order_id] = (account_id, flow_id)

    def orders_of_account(self, account_id: UUID) -> PlatformOrders:
        return {order: flow for order, (account, flow) in self.orders.items() if account == account_id}
