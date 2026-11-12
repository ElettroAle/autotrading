from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.trade_intent import TradeSide


@dataclass(frozen=True, slots=True)
class AccountPosition:
    """A position open on the account as the exchange reports it: its asset says which flow owns it (R1.6.1)."""

    asset: str
    side: TradeSide
    size: Decimal
    margin: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True, slots=True)
class AccountFill:
    """One execution of the account read from the exchange, with the client order id the platform gave, if any."""

    fill_id: str
    order_id: UUID | None
    asset: str
    size: Decimal
    price: Decimal
    fee: Decimal
    realized_pnl: Decimal
    executed_at: datetime


@dataclass(frozen=True, slots=True)
class BalanceMovement:
    """A change of the balance the exchange records outside the executions: a deposit, a withdrawal, a transfer."""

    movement_id: str
    amount: Decimal
    moved_at: datetime


@dataclass(frozen=True, slots=True)
class AccountActivity:
    """What the exchange shows of an account now: the totals, the open positions, the executions, the movements.

    The platform keeps no liquidity of its own: the state of every flow is shared out of this reading (R1.6.1).
    """

    currency: str
    balance: Decimal
    available_margin: Decimal
    positions: tuple[AccountPosition, ...]
    fills: tuple[AccountFill, ...]
    movements: tuple[BalanceMovement, ...]
    read_at: datetime
