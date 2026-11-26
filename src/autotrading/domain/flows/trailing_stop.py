from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TypedDict, Unpack

from autotrading.domain.flows.errors import (
    TrailingActivationNotPositiveError,
    TrailingActivationWithoutDistanceError,
    TrailingBreakevenNotPositiveError,
    TrailingDistanceOutOfRangeError,
)
from autotrading.domain.flows.trade_side import TradeSide

MIN_TRAILING_DISTANCE = Decimal("0.1")
MAX_TRAILING_DISTANCE = Decimal(50)
PERCENT = Decimal(100)


class TrailingParts(TypedDict, total=False):
    """The parts of the stop that follows the price that may change, each by its name."""

    distance_percent: Decimal | None
    activation_percent: Decimal | None
    breakeven_percent: Decimal | None
    max_profit_in_context: bool


@dataclass(frozen=True, slots=True)
class TrailingStop:
    """How the platform moves the stop loss of an open position as the price goes its way, between the cycles (R5.5.1):
    a distance from the best price the position reached, from 0.1 to 50%, followed only once the price went its way by
    the activation, if any; the entry price once the price went its way by the breakeven, if any; and whether the agent
    receives the largest unrealized profit the position reached.

    Every part is empty, the option off, unless the user sets it: without distance and breakeven nothing moves and the
    flow behaves as before. An activation needs the distance it starts.
    """

    distance_percent: Decimal | None = None
    activation_percent: Decimal | None = None
    breakeven_percent: Decimal | None = None
    max_profit_in_context: bool = False

    def __post_init__(self) -> None:
        distance = self.distance_percent
        if distance is not None and not (
            distance.is_finite() and MIN_TRAILING_DISTANCE <= distance <= MAX_TRAILING_DISTANCE
        ):
            raise TrailingDistanceOutOfRangeError
        if not _positive_or_none(self.activation_percent):
            raise TrailingActivationNotPositiveError
        if not _positive_or_none(self.breakeven_percent):
            raise TrailingBreakevenNotPositiveError
        if self.activation_percent is not None and distance is None:
            raise TrailingActivationWithoutDistanceError

    def changed(self, **parts: Unpack[TrailingParts]) -> TrailingStop:
        """The stop with the parts given; a part not given keeps its value."""
        return replace(self, **parts)

    @property
    def active(self) -> bool:
        """Only a distance or a breakeven moves the stop: only their positions are watched."""
        return self.distance_percent is not None or self.breakeven_percent is not None

    @property
    def max_profit_for_agent(self) -> bool:
        """The option has effect only on the positions the platform watches."""
        return self.active and self.max_profit_in_context

    def stop_of(self, side: TradeSide, entry_price: Decimal, best_price: Decimal) -> Decimal | None:
        """The stop the platform computes for a position from the best price it reached: at the distance from it once
        the activation is reached, at the entry price once the breakeven is, the one closer to the price of the two;
        None while neither applies.
        """
        gained = _gained_percent(side, entry_price, best_price)
        candidates: list[Decimal] = []
        distance, activation = self.distance_percent, self.activation_percent
        if distance is not None and (activation is None or gained >= activation):
            candidates.append(best_price * (1 - _sign(side) * distance / PERCENT))
        if self.breakeven_percent is not None and gained >= self.breakeven_percent:
            candidates.append(entry_price)
        if not candidates:
            return None
        return max(candidates) if side is TradeSide.LONG else min(candidates)

    def moved_stop(
        self, side: TradeSide, entry_price: Decimal, best_price: Decimal, in_force: Decimal | None
    ) -> Decimal | None:
        """The stop the position moves to, only when it lies closer to the price than the one in force: the stop never
        goes away from the price.
        """
        computed = self.stop_of(side, entry_price, best_price)
        if computed is None:
            return None
        if in_force is not None and not TrailingStop.farther(in_force, computed, side):
            return None
        return computed

    @staticmethod
    def farther(stop: Decimal, other: Decimal, side: TradeSide) -> bool:
        """Whether the first stop lies farther from the price than the second: lower for a long, higher for a short."""
        return stop < other if side is TradeSide.LONG else stop > other

    @staticmethod
    def best_price(side: TradeSide, previous: Decimal | None, price: Decimal) -> Decimal:
        """The best price after this one: the highest for a long, the lowest for a short; the price itself first."""
        if previous is None:
            return price
        return max(previous, price) if side is TradeSide.LONG else min(previous, price)


def _positive_or_none(percent: Decimal | None) -> bool:
    return percent is None or (percent.is_finite() and percent > 0)


def _sign(side: TradeSide) -> int:
    """Where the price goes the way of the position: up for a long, down for a short."""
    return 1 if side is TradeSide.LONG else -1


def _gained_percent(side: TradeSide, entry_price: Decimal, best_price: Decimal) -> Decimal:
    return _sign(side) * (best_price - entry_price) / entry_price * PERCENT
