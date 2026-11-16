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

    def updated(self, change: ExitPlanChange, placed: PlacedLevels) -> ExitPlan:
        """The plan after an update: the levels waiting on the exchange, which an update the exchange refused leaves as
        they were, and the new invalidation or the one in force (R3.1.3).
        """
        return ExitPlan(placed.take_profit, placed.stop, change.invalidation or self.invalidation)


@dataclass(frozen=True, slots=True)
class ExitPlanChange:
    """How the agent changes the plan of a position already open: a new target, stop or invalidation, each optional
    (none keeps the one in force), or the target removed. The stop is never removed (R3.1.3).
    """

    target: Decimal | None = None
    stop: Decimal | None = None
    invalidation: str | None = None
    remove_target: bool = False

    def coherent_with(
        self, side: TradeSide, market_price: Decimal
    ) -> tuple[ExitPlanChange, tuple[DiscardedLevel, ...]]:
        """The change without the prices incoherent with the side of the position, by the rule of an opening: a level
        discarded leaves the one in force (R3.1.3).
        """
        plan, discarded = ExitPlan(self.target, self.stop, self.invalidation).coherent_with(side, market_price)
        return replace(self, target=plan.target, stop=plan.stop), discarded


@dataclass(frozen=True, slots=True)
class PlacedLevels:
    """The stop loss and the take profit waiting on the exchange for a position of a flow (R3.1.2, R3.1.3)."""

    stop: Decimal | None
    take_profit: Decimal | None


def _gains(exit_price: Decimal, entry_price: Decimal, side: TradeSide) -> bool:
    """Whether leaving at the first price gains on the second: higher for a long, lower for a short."""
    return exit_price > entry_price if side is TradeSide.LONG else exit_price < entry_price


def _discarded(label: str, price: Decimal, side: TradeSide, market_price: Decimal) -> DiscardedLevel:
    reason = f"{label} {number_text(price)} scartato: incoerente con {side.value} al prezzo {number_text(market_price)}"
    return DiscardedLevel(price, reason)
