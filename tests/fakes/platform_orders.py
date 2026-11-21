"""Fake of the orders the platform sent: client order id, account and the flow that sent it, if any, and the
protections it placed for the flows (R3.1.2)."""

from collections.abc import Callable, Iterable
from uuid import UUID

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import PlatformOrder, PlatformOrders
from autotrading.domain.orders.order import Order, OrderOrigin
from autotrading.domain.orders.protection_kind import ProtectionKind
from tests.fakes.protection_repository import ProtectionStore

REASON_OF = {ProtectionKind.STOP_LOSS: CloseReason.STOP_LOSS, ProtectionKind.TAKE_PROFIT: CloseReason.TAKE_PROFIT}


def no_recorded_orders() -> list[Order]:
    return []


class InMemoryPlatformOrdersAdapter:
    """The orders a test names, and the orders the platform recorded when a test hands them over, read as the real
    adapter reads the table of the orders: the flow of each one, and whether the verification procedure sent it."""

    def __init__(
        self, protections: ProtectionStore | None = None, recorded: Callable[[], Iterable[Order]] = no_recorded_orders
    ) -> None:
        self.orders: dict[UUID, tuple[UUID, PlatformOrder]] = {}
        self.asked: list[frozenset[UUID]] = []
        self._protections = protections or ProtectionStore()
        self._recorded = recorded

    def add(self, order_id: UUID, account_id: UUID, flow_id: FlowId | None, *, verification: bool = False) -> None:
        self.orders[order_id] = (account_id, PlatformOrder(flow_id, verification))

    def orders_among(self, account_id: UUID, order_ids: Iterable[UUID]) -> PlatformOrders:
        wanted = set(order_ids)
        self.asked.append(frozenset(wanted))
        recorded = {
            order.id.value: _platform_order_of(order)
            for order in self._recorded()
            if order.request.account_id == account_id and order.id.value in wanted
        }
        sent = {
            order: sent for order, (account, sent) in self.orders.items() if account == account_id and order in wanted
        }
        placed = {
            protection.client_order_id.value: PlatformOrder(
                FlowId(protection.flow_id), protection=REASON_OF[protection.kind]
            )
            for _, protection in self._protections.placed
            if protection.account_id == account_id and protection.client_order_id.value in wanted
        }
        return recorded | sent | placed


def _platform_order_of(order: Order) -> PlatformOrder:
    source = order.request.source
    flow_id = None if source.flow_id is None else FlowId(source.flow_id)
    return PlatformOrder(flow_id, verification=source.origin is OrderOrigin.VERIFICATION)
