from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.trade_intent import OpenIntent
from autotrading.domain.flows.trade_side import TradeSide


class AdjustmentKind(StrEnum):
    LEVERAGE = "leva"
    MARGIN = "margine"
    VALUE = "valore"
    TOTAL_MARGIN = "margine complessivo"
    TOTAL_VALUE = "valore complessivo"
    EXIT_PLAN = "piano di uscita"


@dataclass(frozen=True, slots=True)
class Adjustment:
    """A change the risk check made to an opening, recorded with what the agent asked and why.

    Per operation (R1.5.1-R1.5.4) or on the sum of the open positions of the flow (R3.2.1). A level of the exit plan
    incoherent with the side is removed: nothing comes after it (R3.1.1).
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
        opening: Callable[[str, str, Decimal, int, Decimal | None, Decimal | None], T],
        closing: Callable[[str, bool], T],  # noqa: ARG002 - each outcome builds one of the orders
        updating: Callable[[str, Decimal | None, Decimal | None, bool], T],  # noqa: ARG002 - each outcome builds one of the orders
    ) -> T:
        """The order that executes the opening, built by whoever sends it: asset, side, value, leverage, and the stop
        and target of its exit plan that its protection follows (R3.1.2).
        """
        plan = self.exit_plan
        return opening(self.asset, self.side.value, self.value, self.leverage, plan.stop, plan.target)


@dataclass(frozen=True, slots=True)
class ApprovedClose:
    """A close the risk check lets through, always total (R1.4.4). The close of a reversal carries the opening on the
    opposite side, which waits for the close to be executed and is checked on the state after it (R1.4.10).
    """

    asset: str
    reopening: OpenIntent | None = None

    @property
    def reason(self) -> CloseReason:
        """Why the position closes, as its history keeps it (R1.7.2)."""
        return CloseReason.AGENT if self.reopening is None else CloseReason.REVERSAL

    def order_with[T](
        self,
        opening: Callable[[str, str, Decimal, int, Decimal | None, Decimal | None], T],  # noqa: ARG002 - one of the orders
        closing: Callable[[str, bool], T],
        updating: Callable[[str, Decimal | None, Decimal | None, bool], T],  # noqa: ARG002 - one of the orders
    ) -> T:
        """The order that executes the close, built by whoever sends it: the asset, and whether it reverses the
        position.
        """
        return closing(self.asset, self.reopening is not None)


@dataclass(frozen=True, slots=True)
class ApprovedUpdate:
    """An update of the exit plan of an open position the risk check lets through, with only the levels coherent with
    its side and the notes of those it discarded (R3.1.3).
    """

    asset: str
    plan_change: ExitPlanChange
    adjustments: tuple[Adjustment, ...]

    def order_with[T](
        self,
        opening: Callable[[str, str, Decimal, int, Decimal | None, Decimal | None], T],  # noqa: ARG002 - one of the orders
        closing: Callable[[str, bool], T],  # noqa: ARG002 - one of the orders
        updating: Callable[[str, Decimal | None, Decimal | None, bool], T],
    ) -> T:
        """The order that replaces the protection of the position, built by whoever sends it: asset, new stop, new
        target and whether the target goes (R3.1.3).
        """
        change = self.plan_change
        return updating(self.asset, change.stop, change.target, change.remove_target)


@dataclass(frozen=True, slots=True)
class BlockedDecision:
    """A decision that produces no order: recorded with the reason, the other decisions go on (R1.5.3)."""

    asset: str
    reason: str

    @classmethod
    def opening(cls, asset: str, cause: str) -> BlockedDecision:
        return cls(asset, f"{_opening_not_executed(asset)}{cause}")

    @property
    def cause(self) -> str:
        """Why the decision is blocked, without naming the opening the reason may begin with (R3.5.1)."""
        return self.reason.removeprefix(_opening_not_executed(self.asset))

    @classmethod
    def without_reversible_position(cls, asset: str) -> BlockedDecision:
        """A reversal needs the position of the flow it turns (R1.4.10, R1.5.3)."""
        return cls(asset, "nessuna posizione da invertire")

    @classmethod
    def closing_not_executed(cls, asset: str) -> BlockedDecision:
        """The opening of a reversal is never sent while the position it follows is still open (R1.4.10)."""
        return cls.opening(asset, "chiusura non eseguita")

    @classmethod
    def untradable(cls, asset: str) -> BlockedDecision:
        return cls(asset, f"asset non negoziabile sull'exchange: {asset}")

    @classmethod
    def without_position(cls, asset: str) -> BlockedDecision:
        return cls(asset, f"nessuna posizione aperta su {asset}")

    @classmethod
    def below_minimum_confidence(cls, asset: str, confidence: int, minimum: MinimumConfidence) -> BlockedDecision:
        return cls.opening(asset, f"confidenza {confidence} sotto la minima {minimum}")


def _opening_not_executed(asset: str) -> str:
    return f"apertura {asset} non eseguita: "


@dataclass(frozen=True, slots=True)
class HeldPosition:
    asset: str


type RiskOutcome = ApprovedOpening | ApprovedClose | ApprovedUpdate | BlockedDecision | HeldPosition
type ApprovedOutcome = ApprovedOpening | ApprovedClose | ApprovedUpdate


def approved_of(outcomes: Iterable[RiskOutcome]) -> tuple[ApprovedOutcome, ...]:
    """Only the approved decisions become orders (R1.5.5, R3.1.3)."""
    return tuple(
        outcome for outcome in outcomes if isinstance(outcome, (ApprovedOpening, ApprovedClose, ApprovedUpdate))
    )
