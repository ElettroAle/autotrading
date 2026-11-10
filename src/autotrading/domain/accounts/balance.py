from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Balance:
    """The value of the account as the exchange reports it, in the currency of its margin."""

    amount: Decimal
    currency: str
