from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.trade_side import TradeSide


class AdjustmentKind(StrEnum):
    LEVERAGE = "leva"
    MARGIN = "margine"
    VALUE = "valore"
    EXIT_PLAN = "piano di uscita"


@dataclass(frozen=True, slots=True)
class Adjustment:
    """A change the risk check made to an opening, recorded with what the agent asked and why (R1.5.1-R1.5.4).

    A level of the exit plan incoherent with the side is removed: nothing comes after it (R3.1.1).
    """

    kind: AdjustmentKind
    before: Decimal
    after: Decimal | None
    reason: str


@dataclass(frozen=True, slots=True)
class ApprovedOpening:
    """An opening the risk check lets through: its value is what the order sizes, the margin follows from it; its exit
    plan holds only the levels coherent with its side (R3.1.1).
    """

    asset: str
    side: TradeSide
    value: Decimal
    leverage: int
    adjustments: tuple[Adjustment, ...]
    exit_plan: ExitPlan = field(default_factory=ExitPlan)

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


def approved_of(outcomes: Iterable[RiskOutcome]) -> tuple[ApprovedOpening | ApprovedClose, ...]:
    """Only the approved decisions become orders (R1.5.5)."""
    return tuple(outcome for outcome in outcomes if isinstance(outcome, (ApprovedOpening, ApprovedClose)))
