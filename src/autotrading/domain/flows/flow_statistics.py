from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.flow_cost import FlowCost

PERCENT = Decimal(100)


@dataclass(frozen=True, slots=True)
class FlowStatistics:
    """The quality of the strategy of a flow over a period (R2.2.6).

    An operation is a position closed in the period: won with a positive net result, lost with a negative one, neither
    when even. An even operation counts among the operations but not in the win rate, which is won over won and lost
    and is not available without a won or lost operation. The model cost leaves the calls whose cost nobody knows
    apart, as the cost of the flow does (R1.4.6).
    """

    won: int
    lost: int
    operations: int
    win_rate_percent: Decimal | None
    average_winning_pnl: Decimal | None
    average_losing_pnl: Decimal | None
    total_fees: Decimal
    model_cost_usd: Decimal
    model_calls_without_cost: int

    @classmethod
    def of(cls, positions: Iterable[ClosedPosition], cost: FlowCost) -> FlowStatistics:
        closed = list(positions)
        winning = [position.net_pnl for position in closed if position.net_pnl > 0]
        losing = [position.net_pnl for position in closed if position.net_pnl < 0]
        return cls(
            won=len(winning),
            lost=len(losing),
            operations=len(closed),
            win_rate_percent=_win_rate(len(winning), len(losing)),
            average_winning_pnl=_average(winning),
            average_losing_pnl=_average(losing),
            total_fees=sum((position.fees for position in closed), Decimal(0)),
            model_cost_usd=cost.total_usd,
            model_calls_without_cost=cost.unavailable_calls,
        )


def _win_rate(won: int, lost: int) -> Decimal | None:
    decisive = won + lost
    if decisive == 0:
        return None
    return Decimal(won) / Decimal(decisive) * PERCENT


def _average(results: Sequence[Decimal]) -> Decimal | None:
    if not results:
        return None
    return sum(results, Decimal(0)) / len(results)
