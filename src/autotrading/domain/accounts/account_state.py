from dataclasses import dataclass
from datetime import datetime

from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.position import Position


@dataclass(frozen=True, slots=True)
class AccountState:
    """The account read from the exchange at the request, never from a saved copy (R0.2.2)."""

    balance: Balance
    available_margin: Balance
    positions: tuple[Position, ...]
    read_at: datetime
