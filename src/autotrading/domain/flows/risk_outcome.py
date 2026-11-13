from collections.abc import Iterable
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


@dataclass(frozen=True, slots=True)
class ApprovedClose:
    asset: str


@dataclass(frozen=True, slots=True)
class BlockedDecision:
    """A decision that produces no order: recorded with the reason, the other decisions go on (R1.5.3)."""

    asset: str
    reason: str


@dataclass(frozen=True, slots=True)
class HeldPosition:
    asset: str


type RiskOutcome = ApprovedOpening | ApprovedClose | BlockedDecision | HeldPosition


def approved_of(outcomes: Iterable[RiskOutcome]) -> tuple[ApprovedOpening | ApprovedClose, ...]:
    """Only the approved decisions become orders (R1.5.5)."""
    return tuple(outcome for outcome in outcomes if isinstance(outcome, (ApprovedOpening, ApprovedClose)))
