from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal

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
    min_order_value: Decimal
    # What a price admits, when the exchange limits it: so many significant figures, though a whole price keeps every
    # digit, and at most so many decimals (R3.1.2).
    price_significant_figures: int | None = None
    price_decimals: int | None = None
    # The share of the value of an order taken by the exchange at the market price (R6.3.2); none when unknown.
    taker_fee_rate: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if (
            self.max_leverage < 1
            or self.size_decimals < 0
            or self.mid_price <= 0
            or self.min_order_value < 0
            or self.taker_fee_rate < 0
        ):
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
        """The size worth `value` at the current price, rounded down to the step.

        A value that meets the exchange minimum is rounded up instead when rounding down would fall below it: the
        exchange would refuse an order the risk check approved (R1.5.5).
        """
        size = (value / self.mid_price).quantize(self.size_step, rounding=ROUND_DOWN)
        if value >= self.min_order_value and size * self.mid_price < self.min_order_value:
            size = (value / self.mid_price).quantize(self.size_step, rounding=ROUND_UP)
        if size <= 0:
            raise OrderSizeBelowStepError(self.coin, self.size_step)
        return size

    def rounded_price(self, price: Decimal) -> Decimal:
        """The price to the nearest one the exchange admits for an order at a price: a stop loss, a take profit."""
        admitted = [limit for limit in (self._significant_decimals(price), self.price_decimals) if limit is not None]
        if not admitted:
            return price
        return price.quantize(Decimal(1).scaleb(-max(min(admitted), 0)), rounding=ROUND_HALF_UP)

    def _significant_decimals(self, price: Decimal) -> int | None:
        """The decimals that keep the significant figures: none for a price whose whole part has them all."""
        if self.price_significant_figures is None:
            return None
        return self.price_significant_figures - price.adjusted() - 1
