"""Fake of the orders the platform sent: client order id, account and the flow that sent it, if any."""

from collections.abc import Iterable
from uuid import UUID

from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import PlatformOrder, PlatformOrders


class InMemoryPlatformOrdersAdapter:
    def __init__(self) -> None:
        self.orders: dict[UUID, tuple[UUID, PlatformOrder]] = {}
        self.asked: list[frozenset[UUID]] = []

    def add(self, order_id: UUID, account_id: UUID, flow_id: FlowId | None, *, verification: bool = False) -> None:
        self.orders[order_id] = (account_id, PlatformOrder(flow_id, verification))

    def orders_among(self, account_id: UUID, order_ids: Iterable[UUID]) -> PlatformOrders:
        wanted = set(order_ids)
        self.asked.append(frozenset(wanted))
        return {
            order: sent for order, (account, sent) in self.orders.items() if account == account_id and order in wanted
        }
