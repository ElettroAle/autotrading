from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
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
