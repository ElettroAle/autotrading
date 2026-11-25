from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.agent.exit_plan import ExitPlan, ExitPlanChange


class TradeAction(StrEnum):
    """The only actions the agent may take on an asset (R1.4.3, R1.4.4); an update changes the exit plan of a position
    already open (R3.1.3); a reversal closes the open position and opens the opposite side in the same cycle (R1.4.10).
    """

    OPEN = "apri"
    CLOSE = "chiudi"
    HOLD = "mantieni"
    UPDATE = "aggiorna"
    REVERSE = "inverti"


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
class TradeReversal:
    """The operational fields of a reversal: those of an opening but the direction, always the opposite of the position
    open (R1.4.10).
    """

    margin_fraction: Decimal
    leverage: int
    exit_plan: ExitPlan = field(default_factory=ExitPlan)


@dataclass(frozen=True, slots=True)
class Decision:
    """A conforming decision of the agent on one asset, with its reasoning and how convinced of it the agent is, from 0
    to 100 (R1.4.4, R3.1.4).

    Only an opening and a reversal carry operational fields and only an update the change of the plan (R3.1.3); a
    close is always total. The motive in one sentence is None when the model gave none (R5.3.5).
    """

    asset: str
    action: TradeAction
    reasoning: str
    confidence: int
    opening: TradeOpening | None = None
    plan_change: ExitPlanChange | None = None
    reversal: TradeReversal | None = None
    motive: str | None = None

    def intent_with[O, C, H, U, R](
        self,
        opening: Callable[[str, str, Decimal, int, ExitPlan, int], O],
        closing: Callable[[str], C],
        holding: Callable[[str], H],
        updating: Callable[[str, ExitPlanChange], U],
        reversing: Callable[[str, Decimal, int, ExitPlan, int], R],
    ) -> O | C | H | U | R:
        """What the decision asks, built by whoever checks it: an opening, an update or a reversal without its fields
        holds the asset; an opening and a reversal carry the confidence, which a minimum confidence may stop (R3.1.4,
        R1.4.10).
        """
        if self.action is TradeAction.CLOSE:
            return closing(self.asset)
        if self.action is TradeAction.UPDATE and self.plan_change is not None:
            return updating(self.asset, self.plan_change)
        if self.action is TradeAction.REVERSE and self.reversal is not None:
            reversal = self.reversal
            return reversing(
                self.asset, reversal.margin_fraction, reversal.leverage, reversal.exit_plan, self.confidence
            )
        if self.action is TradeAction.OPEN and self.opening is not None:
            fields = self.opening
            return opening(
                self.asset,
                fields.direction.value,
                fields.margin_fraction,
                fields.leverage,
                fields.exit_plan,
                self.confidence,
            )
        return holding(self.asset)


@dataclass(frozen=True, slots=True)
class DiscardedDecision:
    """A decision that does not conform: it never reaches the risk check, and is recorded with the reason (R1.4.5)."""

    asset: str
    reason: str
