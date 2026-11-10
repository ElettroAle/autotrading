from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class Position:
    """An open position as the exchange reports it at the moment of the reading (R0.2.2)."""

    coin: str
    side: PositionSide
    size: Decimal
    leverage: int
    entry_price: Decimal
    unrealized_pnl: Decimal
    # The exchange reports no liquidation price when the margin covers any move of the price.
    liquidation_price: Decimal | None
