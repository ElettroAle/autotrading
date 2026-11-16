from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.agent.exit_plan import ExitPlan, ExitPlanChange


class TradeAction(StrEnum):
    """The only actions the agent may take on an asset (R1.4.3, R1.4.4); an update changes the exit plan of a position
    already open (R3.1.3).
    """

    OPEN = "apri"
    CLOSE = "chiudi"
    HOLD = "mantieni"
    UPDATE = "aggiorna"


class TradeDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class TradeOpening:
    """The operational fields of an opening: the share of the flow capital committed as margin, the leverage and the
    exit plan (R1.4.4, R3.1.1).
    """

    direction: TradeDirection
    margin_fraction: Decimal
    leverage: int
    exit_plan: ExitPlan = field(default_factory=ExitPlan)


@dataclass(frozen=True, slots=True)
class Decision:
    """A conforming decision of the agent on one asset, with its reasoning (R1.4.4).

    Only an opening carries operational fields and only an update the change of the plan (R3.1.3); a close is always
    total.
    """

    asset: str
    action: TradeAction
    reasoning: str
    opening: TradeOpening | None = None
    plan_change: ExitPlanChange | None = None

    def intent_with[O, C, H, U](
        self,
        opening: Callable[[str, str, Decimal, int, ExitPlan], O],
        closing: Callable[[str], C],
        holding: Callable[[str], H],
        updating: Callable[[str, ExitPlanChange], U],
    ) -> O | C | H | U:
        """What the decision asks, built by whoever checks it: an opening or an update without its fields holds the
        asset.
        """
        if self.action is TradeAction.CLOSE:
            return closing(self.asset)
        if self.action is TradeAction.UPDATE and self.plan_change is not None:
            return updating(self.asset, self.plan_change)
        if self.action is TradeAction.OPEN and self.opening is not None:
            fields = self.opening
            return opening(
                self.asset, fields.direction.value, fields.margin_fraction, fields.leverage, fields.exit_plan
            )
        return holding(self.asset)


@dataclass(frozen=True, slots=True)
class DiscardedDecision:
    """A decision that does not conform: it never reaches the risk check, and is recorded with the reason (R1.4.5)."""

    asset: str
    reason: str
