from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from autotrading.domain.orders.errors import (
    InvalidLeverageError,
    InvalidMarketError,
    LeverageAboveMaximumError,
    OrderSizeBelowStepError,
)


@dataclass(frozen=True, slots=True)
class Market:
    """What the exchange admits for an asset, and its current price: the rules an order must respect."""

    coin: str
    max_leverage: int
    size_decimals: int
    mid_price: Decimal

    def __post_init__(self) -> None:
        if self.max_leverage < 1 or self.size_decimals < 0 or self.mid_price <= 0:
            raise InvalidMarketError(self.coin)

    @property
    def size_step(self) -> Decimal:
        return Decimal(1).scaleb(-self.size_decimals)

    def require_leverage(self, leverage: int) -> None:
        if leverage < 1:
            raise InvalidLeverageError(leverage)
        if leverage > self.max_leverage:
            raise LeverageAboveMaximumError(self.coin, self.max_leverage)

    def size_for(self, value: Decimal) -> Decimal:
        """The size worth `value` at the current price, rounded down to the step: never more than asked."""
        size = (value / self.mid_price).quantize(self.size_step, rounding=ROUND_DOWN)
        if size <= 0:
            raise OrderSizeBelowStepError(self.coin, self.size_step)
        return size
