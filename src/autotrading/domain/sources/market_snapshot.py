from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """The current values of an asset on the exchange: mark price, mid price, open interest, funding rate (R1.3.3)."""

    price: Decimal
    mid: Decimal
    open_interest: Decimal
    funding_rate: Decimal
