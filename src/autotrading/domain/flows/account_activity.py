from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.trade_intent import TradeSide

PERCENT = Decimal(100)


@dataclass(frozen=True, slots=True)
class AccountPosition:
    """A position open on the account as the exchange reports it: its asset says which flow owns it (R1.6.1)."""

    asset: str
    side: TradeSide
    size: Decimal
    margin: Decimal
    unrealized_pnl: Decimal
    leverage: int
    entry_price: Decimal

    @property
    def unrealized_pnl_percent(self) -> Decimal | None:
        """The unrealized PnL on the margin the position holds; without margin there is nothing to measure it on."""
        if self.margin == 0:
            return None
        return self.unrealized_pnl / self.margin * PERCENT


@dataclass(frozen=True, slots=True)
class BalanceMovement:
    """A change of the balance the exchange records outside the executions: a deposit, a withdrawal, a transfer."""

    movement_id: str
    amount: Decimal
    moved_at: datetime


@dataclass(frozen=True, slots=True)
class AccountActivity:
    """What the exchange shows of an account now: the totals, the open positions, the movements of the balance.

    The executions are not part of it: the platform records them in its ledger as they happen (ADR 0063).
    """

    currency: str
    balance: Decimal
    available_margin: Decimal
    positions: tuple[AccountPosition, ...]
    movements: tuple[BalanceMovement, ...]
    read_at: datetime

    @property
    def open_assets(self) -> frozenset[str]:
        """The assets with a position open on the account: the one place that decides it for the flows context."""
        return frozenset(position.asset for position in self.positions)
