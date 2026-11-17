from dataclasses import dataclass

from autotrading.domain.flows.errors import UnknownFilteredActionError, UnknownFilteredDirectionError
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide


@dataclass(frozen=True, slots=True)
class DecisionFilter:
    """What the user asks of the history of the decisions of a flow: asset, action and direction (R6.5.5).

    A missing value does not narrow; only an opening has a direction, so a direction leaves out every other action.
    """

    asset: str | None = None
    action: DecisionAction | None = None
    direction: TradeSide | None = None

    @classmethod
    def named(cls, asset: str | None = None, action: str | None = None, direction: str | None = None) -> DecisionFilter:
        return cls(asset, _action_named(action), _direction_named(direction))

    def matches(self, decision: RecordedDecision) -> bool:
        return (
            (self.asset is None or decision.asset == self.asset)
            and (self.action is None or decision.action is self.action)
            and (self.direction is None or decision.direction is self.direction)
        )


def _action_named(name: str | None) -> DecisionAction | None:
    if name is None:
        return None
    actions = {action.value: action for action in DecisionAction}
    if name not in actions:
        raise UnknownFilteredActionError(tuple(actions))
    return actions[name]


def _direction_named(name: str | None) -> TradeSide | None:
    if name is None:
        return None
    directions = {direction.value: direction for direction in TradeSide}
    if name not in directions:
        raise UnknownFilteredDirectionError(tuple(directions))
    return directions[name]
