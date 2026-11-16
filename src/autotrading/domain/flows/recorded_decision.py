from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from autotrading.domain.flows.errors import (
    DecisionConfidenceOutOfRangeError,
    DirectionWithoutOpeningError,
    UnknownDecisionActionError,
    UnknownDecisionDirectionError,
)
from autotrading.domain.flows.trade_side import TradeSide

LOWEST_CONFIDENCE, HIGHEST_CONFIDENCE = 0, 100


class DecisionAction(StrEnum):
    """What the agent decided on an asset, as the cycle records it: the words of its actions (R1.4.3, R3.1.3)."""

    OPEN = "apri"
    CLOSE = "chiudi"
    HOLD = "mantieni"
    UPDATE = "aggiorna"


@dataclass(frozen=True, slots=True)
class RecordedDecision:
    """A decision of the agent on one asset as a cycle recorded it (R6.5.4, ADR
    decisioni-del-ciclo-registrate-per-asset).

    Only an opening has a direction; the confidence is None for the decisions recorded before the agent gave one
    (R3.1.4).
    """

    asset: str
    action: DecisionAction
    direction: TradeSide | None
    confidence: int | None
    reasoning: str

    def __post_init__(self) -> None:
        if self.direction is not None and self.action is not DecisionAction.OPEN:
            raise DirectionWithoutOpeningError(self.direction, self.action)
        if self.confidence is not None and not LOWEST_CONFIDENCE <= self.confidence <= HIGHEST_CONFIDENCE:
            raise DecisionConfidenceOutOfRangeError

    @classmethod
    def named(
        cls, asset: str, action: str, direction: str | None, confidence: int | None, reasoning: str
    ) -> RecordedDecision:
        """The decision from the words the record keeps."""
        return cls(asset, _action_named(action), _direction_named(direction), confidence, reasoning)


@dataclass(frozen=True, slots=True)
class DecidedCycle:
    """The planned instant of a cycle and the decisions the agent took in it (R6.5.4)."""

    planned_at: datetime
    decisions: tuple[RecordedDecision, ...]


def _action_named(name: str) -> DecisionAction:
    actions = {action.value: action for action in DecisionAction}
    if name not in actions:
        raise UnknownDecisionActionError(name)
    return actions[name]


def _direction_named(name: str | None) -> TradeSide | None:
    if name is None:
        return None
    sides = {side.value: side for side in TradeSide}
    if name not in sides:
        raise UnknownDecisionDirectionError(name)
    return sides[name]
