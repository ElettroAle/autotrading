from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.trade_side import TradeSide


@dataclass(frozen=True, slots=True)
class CyclePosition:
    """A position open on the account as the exchange shows it to a cycle, with what the agent reads of it."""

    asset: str
    side: TradeSide
    size: Decimal
    leverage: int
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    liquidation_price: Decimal | None


@dataclass(frozen=True, slots=True)
class CycleAccount:
    """The account of the flow at the start of a cycle: the margin it has free, which no flow may go beyond, the
    details of its open positions (ADR 0062) and its balance, which the limit of the exposure of its flows on one side
    is a percent of (R5.5.5); all from one reading of the exchange.
    """

    currency: str
    available_margin: Decimal
    positions: tuple[CyclePosition, ...]
    balance: Decimal
