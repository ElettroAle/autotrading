"""Fake of the protections on the exchange: what waits for its price on each account and asset, and what is refused."""

from dataclasses import dataclass

from autotrading.application.orders.errors import ExchangeRejectedOrderError, OrderExchangeUnavailableError
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ActiveProtection, ProtectionOrder
from autotrading.domain.orders.trading_access import TradingAccess

NEVER_PLACED = "Order was never placed, already canceled, or filled."


@dataclass(frozen=True, slots=True)
class Resting:
    """A protection waiting on the exchange, with the order that placed it."""

    order_id: str
    order: ProtectionOrder

    @property
    def active(self) -> ActiveProtection:
        return ActiveProtection(self.order_id, self.order.kind, self.order.trigger_price)


class FakeProtectionExchangeAdapter:
    """Stop loss and take profit of every account: placed, cancelled, executed by the price, or refused by kind.

    It remembers every protection it placed by its client order id, as the exchange does after it leaves.
    """

    def __init__(self) -> None:
        self.resting: dict[tuple[str, str], list[Resting]] = {}
        self.placed: list[ProtectionOrder] = []
        self.cancelled: list[str] = []
        self.rejections: dict[ProtectionKind, str] = {}
        self.reachable = True
        self.known: dict[ClientOrderId, str] = {}
        self.lookups: list[ClientOrderId] = []
        # The next placements that never reach the exchange, and the next ones it places but whose answer is lost.
        self.unreached_placements = 0
        self.lost_placements = 0
        # The kinds whose next placement never reaches the exchange, once each.
        self.unreached_kinds: list[ProtectionKind] = []
        # The next cancellations it makes but whose answer is lost, and the next readings that fail.
        self.lost_cancellations = 0
        self.unreached_readings = 0
        self._next_id = 1000

    def place(self, access: TradingAccess, order: ProtectionOrder) -> str:
        self._require_reachable()
        self.placed.append(order)
        if self.unreached_placements > 0:
            self.unreached_placements -= 1
            raise OrderExchangeUnavailableError
        if order.kind in self.unreached_kinds:
            self.unreached_kinds.remove(order.kind)
            raise OrderExchangeUnavailableError
        rejection = self.rejections.get(order.kind)
        if rejection is not None:
            raise ExchangeRejectedOrderError(rejection)
        self._next_id += 1
        order_id = str(self._next_id)
        self.resting.setdefault(_key(access, order.asset), []).append(Resting(order_id, order))
        self.known[order.client_order_id] = order_id
        if self.lost_placements > 0:
            self.lost_placements -= 1
            raise OrderExchangeUnavailableError
        return order_id

    def find(self, access: TradingAccess, order: ProtectionOrder) -> str | None:  # noqa: ARG002 - one exchange
        self._require_reachable()
        self.lookups.append(order.client_order_id)
        return self.known.get(order.client_order_id)

    def cancel(self, access: TradingAccess, asset: str, order_id: str) -> None:
        self._require_reachable()
        resting = self.resting.get(_key(access, asset), [])
        if not any(each.order_id == order_id for each in resting):
            raise ExchangeRejectedOrderError(NEVER_PLACED)
        self.resting[_key(access, asset)] = [each for each in resting if each.order_id != order_id]
        self.cancelled.append(order_id)
        if self.lost_cancellations > 0:
            self.lost_cancellations -= 1
            raise OrderExchangeUnavailableError

    def active(self, access: TradingAccess, asset: str) -> tuple[ActiveProtection, ...]:
        self._require_reachable()
        if self.unreached_readings > 0:
            self.unreached_readings -= 1
            raise OrderExchangeUnavailableError
        return tuple(each.active for each in self.resting.get(_key(access, asset), []))

    def execute(self, address: str, asset: str, kind: ProtectionKind) -> ProtectionOrder:
        """The price reaches the protection of the kind: it leaves the exchange, executed."""
        resting = self.resting.get((address, asset), [])
        [executed] = [each for each in resting if each.order.kind is kind]
        self.resting[address, asset] = [each for each in resting if each is not executed]
        return executed.order

    def of(self, address: str, asset: str) -> tuple[ProtectionOrder, ...]:
        return tuple(each.order for each in self.resting.get((address, asset), []))

    def _require_reachable(self) -> None:
        if not self.reachable:
            raise OrderExchangeUnavailableError


def _key(access: TradingAccess, asset: str) -> tuple[str, str]:
    return access.value("account_address"), asset
