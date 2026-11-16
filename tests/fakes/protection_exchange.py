"""Fake of the protections on the exchange: what waits for its price on each account and asset, and what is refused."""

from dataclasses import dataclass

from autotrading.application.orders.errors import ExchangeRejectedOrderError, OrderExchangeUnavailableError
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
    """Stop loss and take profit of every account: placed, cancelled, executed by the price, or refused by kind."""

    def __init__(self) -> None:
        self.resting: dict[tuple[str, str], list[Resting]] = {}
        self.placed: list[ProtectionOrder] = []
        self.cancelled: list[str] = []
        self.rejections: dict[ProtectionKind, str] = {}
        self.reachable = True
        self._next_id = 1000

    def place(self, access: TradingAccess, order: ProtectionOrder) -> str:
        self._require_reachable()
        self.placed.append(order)
        rejection = self.rejections.get(order.kind)
        if rejection is not None:
            raise ExchangeRejectedOrderError(rejection)
        self._next_id += 1
        order_id = str(self._next_id)
        self.resting.setdefault(_key(access, order.asset), []).append(Resting(order_id, order))
        return order_id

    def cancel(self, access: TradingAccess, asset: str, order_id: str) -> None:
        self._require_reachable()
        resting = self.resting.get(_key(access, asset), [])
        if not any(each.order_id == order_id for each in resting):
            raise ExchangeRejectedOrderError(NEVER_PLACED)
        self.resting[_key(access, asset)] = [each for each in resting if each.order_id != order_id]
        self.cancelled.append(order_id)

    def active(self, access: TradingAccess, asset: str) -> tuple[ActiveProtection, ...]:
        self._require_reachable()
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
