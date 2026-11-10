from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.orders.errors import InvalidSlippageError

DEFAULT_PERCENT = Decimal(5)
HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class Slippage:
    """The largest distance from the current price a market order accepts; beyond it the order is not executed."""

    fraction: Decimal

    def __post_init__(self) -> None:
        if not Decimal(0) < self.fraction < Decimal(1):
            raise InvalidSlippageError(self.fraction)

    @classmethod
    def percent(cls, value: Decimal) -> Slippage:
        return cls(value / HUNDRED)

    @classmethod
    def default(cls) -> Slippage:
        return cls.percent(DEFAULT_PERCENT)
