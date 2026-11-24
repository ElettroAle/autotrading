from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount


@dataclass(frozen=True, slots=True)
class SimulatedFill:
    """What the simulated exchange executed of an order: its size, price, fee and realized PnL (R6.3.2).

    The position before it is signed, positive for a long, as an exchange reports it beside each execution.
    """

    coin: str
    is_buy: bool
    size: Decimal
    price: Decimal
    fee: Decimal
    realized_pnl: Decimal
    start_position: Decimal
    liquidation: bool
    executed_at: datetime

    @property
    def signed_size(self) -> Decimal:
        return self.size if self.is_buy else -self.size


@dataclass(frozen=True, slots=True)
class SimulatedTrade:
    """A fill and the account as it stands after it."""

    fill: SimulatedFill
    account: SimulatedAccount
