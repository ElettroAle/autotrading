"""Fake of the orders the platform sent: client order id, account and the flow that sent it, if any, and the
protections it placed for the flows (R3.1.2)."""

from collections.abc import Iterable
from uuid import UUID

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import PlatformOrder, PlatformOrders
from autotrading.domain.orders.protection_kind import ProtectionKind
from tests.fakes.protection_repository import ProtectionStore

REASON_OF = {ProtectionKind.STOP_LOSS: CloseReason.STOP_LOSS, ProtectionKind.TAKE_PROFIT: CloseReason.TAKE_PROFIT}


class InMemoryPlatformOrdersAdapter:
    def __init__(self, protections: ProtectionStore | None = None) -> None:
        self.orders: dict[UUID, tuple[UUID, PlatformOrder]] = {}
        self.asked: list[frozenset[UUID]] = []
        self._protections = protections or ProtectionStore()

    def add(self, order_id: UUID, account_id: UUID, flow_id: FlowId | None, *, verification: bool = False) -> None:
        self.orders[order_id] = (account_id, PlatformOrder(flow_id, verification))

    def orders_among(self, account_id: UUID, order_ids: Iterable[UUID]) -> PlatformOrders:
        wanted = set(order_ids)
        self.asked.append(frozenset(wanted))
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
        return sent | placed
