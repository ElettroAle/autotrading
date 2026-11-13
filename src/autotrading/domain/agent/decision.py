from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class TradeAction(StrEnum):
    """The only actions the agent may take on an asset (R1.4.3, R1.4.4)."""

    OPEN = "apri"
    CLOSE = "chiudi"
    HOLD = "mantieni"


class TradeDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class TradeOpening:
    """The operational fields of an opening: the share of the flow capital committed as margin, and the leverage."""

    direction: TradeDirection
    margin_fraction: Decimal
    leverage: int


@dataclass(frozen=True, slots=True)
class Decision:
    """A conforming decision of the agent on one asset, with its reasoning (R1.4.4).

    Only an opening carries operational fields; a close is always total.
    """

    asset: str
    action: TradeAction
    reasoning: str
    opening: TradeOpening | None = None

    def intent_with[O, C, H](
        self,
        opening: Callable[[str, str, Decimal, int], O],
        closing: Callable[[str], C],
        holding: Callable[[str], H],
    ) -> O | C | H:
        """What the decision asks, built by whoever checks it: an opening without its fields holds the asset."""
        if self.action is TradeAction.CLOSE:
            return closing(self.asset)
        if self.action is TradeAction.OPEN and self.opening is not None:
            fields = self.opening
            return opening(self.asset, fields.direction.value, fields.margin_fraction, fields.leverage)
        return holding(self.asset)


@dataclass(frozen=True, slots=True)
class DiscardedDecision:
    """A decision that does not conform: it never reaches the risk check, and is recorded with the reason (R1.4.5)."""

    asset: str
    reason: str
