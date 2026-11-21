from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_cost import FlowCost
from autotrading.domain.flows.flow_return import FlowReturn

PERCENT = Decimal(100)


@dataclass(frozen=True, slots=True)
class FlowStatistics:
    """The quality of the strategy of a flow over a period (R2.2.6).

    An operation is a position closed in the period: won with a positive net result, lost with a negative one, neither
    when even. An even operation counts among the operations but not in the win rate, which is won over won and lost
    and is not available without a won or lost operation. The model cost leaves the calls whose cost nobody knows
    apart, as the cost of the flow does (R1.4.6). The net PnL is the sum of the net results of the operations, the
    PnL the ranking compares (R2.4.2). The return is the one of the period: from the first value the flow recorded in
    it to the last, compounded across the changes of the capital between them as the return of the flow is (R3.4.3,
    ADR rendimento-del-periodo-nelle-statistiche), and not available without a value in the period.
    """

    won: int
    lost: int
    operations: int
    net_pnl: Decimal
    win_rate_percent: Decimal | None
    average_winning_pnl: Decimal | None
    average_losing_pnl: Decimal | None
    total_fees: Decimal
    model_cost_usd: Decimal
    model_calls_without_cost: int
    return_percent: Decimal | None

    @classmethod
    def of(
        cls,
        positions: Iterable[ClosedPosition],
        cost: FlowCost,
        values: Sequence[EquitySnapshot] = (),
        changes: Iterable[CapitalChange] = (),
    ) -> FlowStatistics:
        closed = list(positions)
        winning = [position.net_pnl for position in closed if position.net_pnl > 0]
        losing = [position.net_pnl for position in closed if position.net_pnl < 0]
        return cls(
            won=len(winning),
            lost=len(losing),
            operations=len(closed),
            net_pnl=sum((position.net_pnl for position in closed), Decimal(0)),
            win_rate_percent=_win_rate(len(winning), len(losing)),
            average_winning_pnl=_average(winning),
            average_losing_pnl=_average(losing),
            total_fees=sum((position.fees for position in closed), Decimal(0)),
            model_cost_usd=cost.total_usd,
            model_calls_without_cost=cost.unavailable_calls,
            return_percent=_period_return(values, changes),
        )


def _period_return(values: Sequence[EquitySnapshot], changes: Iterable[CapitalChange]) -> Decimal | None:
    if not values:
        return None
    return FlowReturn.over(values, changes).percent


def _win_rate(won: int, lost: int) -> Decimal | None:
    decisive = won + lost
    if decisive == 0:
        return None
    return Decimal(won) / Decimal(decisive) * PERCENT


def _average(results: Sequence[Decimal]) -> Decimal | None:
    if not results:
        return None
    return sum(results, Decimal(0)) / len(results)
