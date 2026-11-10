from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.slippage import Slippage


@dataclass(frozen=True, slots=True)
class HeldPosition:
    """A position open on the exchange for an asset, as the exchange reports it."""

    coin: str
    direction: Direction
    size: Decimal
    leverage: int

    def closing_order(self, slippage: Slippage) -> MarketOrder:
        """The whole position closed at the market price: reduce only, so it can never open the opposite side."""
        return MarketOrder(self.coin, self.direction, self.size, slippage, reduce_only=True)
