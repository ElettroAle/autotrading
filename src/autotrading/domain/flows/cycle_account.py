from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.trade_intent import TradeSide


@dataclass(frozen=True, slots=True)
class CyclePosition:
    """A position open on the account as the exchange shows it to a cycle, with what the agent reads of it."""

    asset: str
    side: TradeSide
    size: Decimal
    leverage: int
    entry_price: Decimal
    unrealized_pnl: Decimal
    liquidation_price: Decimal | None


@dataclass(frozen=True, slots=True)
class CycleAccount:
    """The account of the flow at the start of a cycle: the margin it has free, which no flow may go beyond, and the
    details of its open positions (ADR 0062).
    """

    currency: str
    available_margin: Decimal
    positions: tuple[CyclePosition, ...]
