from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.orders.errors import (
    ExchangeRejectedOrderError,
    OrderExchangeUnavailableError,
    OrderNotAcknowledgedError,
)
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.trading_access import TradingAccess

EXECUTED_AT = datetime(2026, 11, 10, 12, 0, 1, 250000, tzinfo=UTC)
FEE_RATE = Decimal("0.00045")
# The executed price is never the mid price the size was computed on: the outcome is read, not expected.
PRICE_IMPACT = Decimal("1.0003")
NO_MATCH = "Order could not immediately match against any resting orders. asset=0"
UNKNOWN_ASSET = "Unknown asset"


def default_markets() -> dict[str, Market]:
    return {
        "BTC": Market("BTC", max_leverage=40, size_decimals=5, mid_price=Decimal(100000)),
        "ETH": Market("ETH", max_leverage=25, size_decimals=4, mid_price=Decimal(4000)),
    }


@dataclass(frozen=True)
class FakePosition:
    direction: Direction
    size: Decimal
    leverage: int


class FakeOrderExchangeAdapter:
    """An exchange of orders: markets, leverage and positions of each account, and what each order executed."""

    def __init__(self) -> None:
        self.markets = default_markets()
        self.leverages: dict[tuple[str, str], int] = {}
        self.positions: dict[tuple[str, str], FakePosition] = {}
        self.sent: list[MarketOrder] = []
        self.signers: list[TradingAccess] = []
        self.lookups: list[ClientOrderId] = []
        self.executions: dict[ClientOrderId, Execution] = {}
        self.price_moves: dict[str, Decimal] = {}
        self.rejection: str | None = None
        self.fill_ratio = Decimal(1)
        self.silent = False
        self.executes_when_silent = False
        self.reachable = True

    def position(self, access: TradingAccess, coin: str) -> FakePosition | None:
        return self.positions.get((access.account_address, coin))

    def market(self, access: TradingAccess, coin: str) -> Market:
        self.signers.append(access)
        self._require_reachable()
        market = self.markets.get(coin)
        if market is None:
            raise ExchangeRejectedOrderError(UNKNOWN_ASSET)
        return market

    def set_leverage(self, access: TradingAccess, coin: str, leverage: int) -> None:
        self._require_reachable()
        self.leverages[access.account_address, coin] = leverage

    def place_market_order(self, access: TradingAccess, order: MarketOrder) -> Execution:
        self.sent.append(order)
        self._require_reachable()
        if self.rejection is not None:
            raise ExchangeRejectedOrderError(self.rejection)
        if self.price_moves.get(order.coin, Decimal(0)) > order.slippage.fraction:
            raise ExchangeRejectedOrderError(NO_MATCH)
        if self.silent:
            if self.executes_when_silent:
                self._execute(access, order)
            raise OrderNotAcknowledgedError
        return self._execute(access, order)

    def find_order(self, access: TradingAccess, order: MarketOrder) -> Execution | None:
        self.signers.append(access)
        self.lookups.append(order.id)
        return self.executions.get(order.id)

    def _execute(self, access: TradingAccess, order: MarketOrder) -> Execution:
        price = self.markets[order.coin].mid_price * PRICE_IMPACT
        size = order.size * self.fill_ratio
        execution = Execution(
            size, price, (size * price * FEE_RATE).quantize(Decimal("0.000001")), Decimal(0), EXECUTED_AT
        )
        self.executions[order.id] = execution
        self._move_position(access, order, size)
        return execution

    def _move_position(self, access: TradingAccess, order: MarketOrder, size: Decimal) -> None:
        key = (access.account_address, order.coin)
        current = self.positions.get(key)
        if order.reduce_only and current is not None:
            remaining = current.size - size
            if remaining > 0:
                self.positions[key] = replace(current, size=remaining)
            else:
                del self.positions[key]
            return
        held = Decimal(0) if current is None else current.size
        self.positions[key] = FakePosition(order.direction, held + size, self.leverages.get(key, 1))

    def _require_reachable(self) -> None:
        if not self.reachable:
            raise OrderExchangeUnavailableError
