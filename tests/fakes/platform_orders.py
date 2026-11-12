"""Fake of the orders the platform sent: client order id, account and the flow that sent it, if any."""

from collections.abc import Iterable
from uuid import UUID

from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import PlatformOrders


class InMemoryPlatformOrdersAdapter:
    def __init__(self) -> None:
        self.orders: dict[UUID, tuple[UUID, FlowId | None]] = {}
        self.asked: list[frozenset[UUID]] = []

    def add(self, order_id: UUID, account_id: UUID, flow_id: FlowId | None) -> None:
        self.orders[order_id] = (account_id, flow_id)

    def orders_among(self, account_id: UUID, order_ids: Iterable[UUID]) -> PlatformOrders:
        wanted = set(order_ids)
        self.asked.append(frozenset(wanted))
        return {
            order: flow for order, (account, flow) in self.orders.items() if account == account_id and order in wanted
        }
