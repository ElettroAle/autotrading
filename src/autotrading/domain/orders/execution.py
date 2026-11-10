from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.orders.errors import EmptyExecutionError


@dataclass(frozen=True, slots=True)
class Execution:
    """What the exchange actually executed, read from its fills: never what was expected (R0.3.4)."""

    filled_size: Decimal
    average_price: Decimal
    fee: Decimal
    realized_pnl: Decimal
    executed_at: datetime

    def __post_init__(self) -> None:
        if self.filled_size <= 0:
            raise EmptyExecutionError
