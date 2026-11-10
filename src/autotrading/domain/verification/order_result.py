from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OrderResult:
    """What an order of the procedure did: executed or not, its fee, its realized result and why it failed."""

    succeeded: bool
    fee: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    message: str | None = None
