from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.errors import UnknownPositionResultError, UnknownPositionSideError
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide


class PositionResult(StrEnum):
    """How a closed position went, by its result after the fees, as the statistics count it (R2.2.6, R6.4.4)."""

    WON = "vinta"
    LOST = "persa"


@dataclass(frozen=True, slots=True)
class ClosedPositionFilter:
    """What the user asks of the closed positions of a flow: asset, side, result and minutes of the close (R6.4.4).

    A missing value does not narrow. An even position is neither won nor lost.
    """

    asset: str | None = None
    side: TradeSide | None = None
    result: PositionResult | None = None
    window: TimeWindow = field(default_factory=TimeWindow)

    @classmethod
    def named(
        cls,
        asset: str | None = None,
        side: str | None = None,
        result: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> ClosedPositionFilter:
        return cls(asset, _side_named(side), _result_named(result), TimeWindow.of_minutes(since, until))

    def matches(self, position: ClosedPosition) -> bool:
        return (
            (self.asset is None or position.asset == self.asset)
            and (self.side is None or position.side is self.side)
            and (self.result is None or _result_of(position) is self.result)
            and self.window.contains(position.closing.at)
        )


def _result_of(position: ClosedPosition) -> PositionResult | None:
    if position.net_pnl > 0:
        return PositionResult.WON
    if position.net_pnl < 0:
        return PositionResult.LOST
    return None


def _side_named(name: str | None) -> TradeSide | None:
    if name is None:
        return None
    sides = {side.value: side for side in TradeSide}
    if name not in sides:
        raise UnknownPositionSideError(tuple(sides))
    return sides[name]


def _result_named(name: str | None) -> PositionResult | None:
    if name is None:
        return None
    results = {result.value: result for result in PositionResult}
    if name not in results:
        raise UnknownPositionResultError(tuple(results))
    return results[name]
