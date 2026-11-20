from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Candle:
    """One closed candle of the exchange: the indicators read its close and its volume (R1.3.3), the extended ones its
    high and its low too (R5.1.4)."""

    closed_at: datetime
    close: Decimal
    volume: Decimal
    high: Decimal
    low: Decimal
