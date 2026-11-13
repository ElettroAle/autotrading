from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.flows.trade_intent import TradeSide


class AdjustmentKind(StrEnum):
    LEVERAGE = "leva"
    MARGIN = "margine"
    VALUE = "valore"


@dataclass(frozen=True, slots=True)
class Adjustment:
    """A change the risk check made to an opening, recorded with what the agent asked and why (R1.5.1-R1.5.4)."""

    kind: AdjustmentKind
    before: Decimal
    after: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class ApprovedOpening:
    """An opening the risk check lets through: its value is what the order sizes, the margin follows from it."""

    asset: str
    side: TradeSide
    value: Decimal
    leverage: int
    adjustments: tuple[Adjustment, ...]

    @property
    def margin(self) -> Decimal:
        return self.value / self.leverage

    def order_with[T](
        self,
        opening: Callable[[str, str, Decimal, int], T],
        closing: Callable[[str], T],  # noqa: ARG002 - each outcome builds one of the two orders
    ) -> T:
        """The order that executes the opening, built by whoever sends it: asset, side, value and leverage."""
        return opening(self.asset, self.side.value, self.value, self.leverage)


@dataclass(frozen=True, slots=True)
class ApprovedClose:
    asset: str

    def order_with[T](
        self,
        opening: Callable[[str, str, Decimal, int], T],  # noqa: ARG002 - each outcome builds one of the two orders
        closing: Callable[[str], T],
    ) -> T:
        """The order that executes the close, built by whoever sends it: a close is always total (R1.4.4)."""
        return closing(self.asset)


@dataclass(frozen=True, slots=True)
class BlockedDecision:
    """A decision that produces no order: recorded with the reason, the other decisions go on (R1.5.3)."""

    asset: str
    reason: str


@dataclass(frozen=True, slots=True)
class HeldPosition:
    asset: str


type RiskOutcome = ApprovedOpening | ApprovedClose | BlockedDecision | HeldPosition
