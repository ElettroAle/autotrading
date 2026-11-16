from dataclasses import dataclass, replace
from decimal import Decimal

from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.italian_text import number_text

TARGET_LABEL = "obiettivo"
STOP_LABEL = "stop"


@dataclass(frozen=True, slots=True)
class DiscardedLevel:
    """A price of the plan incoherent with the side of the opening, with the reason the cycle records (R3.1.1)."""

    price: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class ExitPlan:
    """How the agent means to leave a position it opens: target price, stop price and invalidation condition, each
    optional (R3.1.1, RF-17.05).
    """

    target: Decimal | None = None
    stop: Decimal | None = None
    invalidation: str | None = None

    def coherent_with(self, side: TradeSide, market_price: Decimal) -> tuple[ExitPlan, tuple[DiscardedLevel, ...]]:
        """The plan without the prices incoherent with the side at the market price of the exchange of the account.

        For a long a stop at or above the market price, or a target at or below it, is incoherent; for a short the
        opposite. The opening goes on without the level discarded.
        """
        discarded: list[DiscardedLevel] = []
        plan = self
        if self.target is not None and not _gains(self.target, market_price, side):
            plan = replace(plan, target=None)
            discarded.append(_discarded(TARGET_LABEL, self.target, side, market_price))
        if self.stop is not None and not _gains(market_price, self.stop, side):
            plan = replace(plan, stop=None)
            discarded.append(_discarded(STOP_LABEL, self.stop, side, market_price))
        return plan, tuple(discarded)


def _gains(exit_price: Decimal, entry_price: Decimal, side: TradeSide) -> bool:
    """Whether leaving at the first price gains on the second: higher for a long, lower for a short."""
    return exit_price > entry_price if side is TradeSide.LONG else exit_price < entry_price


def _discarded(label: str, price: Decimal, side: TradeSide, market_price: Decimal) -> DiscardedLevel:
    reason = f"{label} {number_text(price)} scartato: incoerente con {side.value} al prezzo {number_text(market_price)}"
    return DiscardedLevel(price, reason)
