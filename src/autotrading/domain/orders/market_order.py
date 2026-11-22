from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.slippage import Slippage


@dataclass(frozen=True, slots=True)
class MarketOrder:
    """An order at the market price within the slippage, as it is sent to the exchange."""

    coin: str
    direction: Direction
    size: Decimal
    slippage: Slippage
    reduce_only: bool = False
    id: ClientOrderId = field(default_factory=ClientOrderId.new)

    @classmethod
    def opening(cls, coin: str, direction: Direction, size: Decimal, slippage: Slippage) -> MarketOrder:
        return cls(coin, direction, size, slippage)

    @property
    def is_buy(self) -> bool:
        # Opening a long buys and closing it sells; the other way round for a short.
        return (self.direction is Direction.LONG) != self.reduce_only

    def limit_price(self, market: Market, oracle_price: Decimal) -> Decimal:
        """The worst price the order accepts: the slippage from the book, but never farther than the slippage from the
        oracle, the true price the exchange measures an order against; a thin book away from it would otherwise give a
        limit the exchange refuses (Bug 631, ADR prezzo-limite-dell-ordine-a-mercato-vicino-all-oracolo).
        """
        if self.is_buy:
            return market.rounded_price(min(market.mid_price, oracle_price) * (1 + self.slippage.fraction))
        return market.rounded_price(max(market.mid_price, oracle_price) * (1 - self.slippage.fraction))
