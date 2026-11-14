from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.errors import RankingWithoutEquityError
from autotrading.domain.flows.flow_statistics import FlowStatistics

PERCENT = Decimal(100)


@dataclass(frozen=True, slots=True)
class FlowRanking:
    """A row of the ranking of the flows over a period (R2.4.2, ADR 0135).

    The return goes from the first to the last equity of the period, and is not available when the first is not
    positive. The maximum drawdown is the largest fall, in percent, of the equity from a previous positive peak of
    the period. The rest are the statistics of the same period (R2.2.6).
    """

    flow_id: UUID
    flow_name: str
    return_percent: Decimal | None
    max_drawdown_percent: Decimal
    statistics: FlowStatistics

    @classmethod
    def of(
        cls, flow_id: UUID, flow_name: str, snapshots: Sequence[EquitySnapshot], statistics: FlowStatistics
    ) -> FlowRanking:
        if not snapshots:
            raise RankingWithoutEquityError
        curve = [snapshot.equity for snapshot in snapshots]
        return cls(flow_id, flow_name, _return_of(curve), _max_drawdown_of(curve), statistics)


def ranked_by_return(rankings: Iterable[FlowRanking]) -> tuple[FlowRanking, ...]:
    """The rows from the highest return; a flow without return closes the ranking, the name breaks a tie."""
    return tuple(sorted(rankings, key=_by_return))


def _by_return(ranking: FlowRanking) -> tuple[bool, Decimal, str]:
    unavailable = ranking.return_percent is None
    return unavailable, -(ranking.return_percent or Decimal(0)), ranking.flow_name


def _return_of(curve: Sequence[Decimal]) -> Decimal | None:
    first, last = curve[0], curve[-1]
    if first <= 0:
        return None
    return (last - first) / first * PERCENT


def _max_drawdown_of(curve: Iterable[Decimal]) -> Decimal:
    peak = Decimal(0)
    deepest = Decimal(0)
    for equity in curve:
        peak = max(peak, equity)
        if peak > 0:
            deepest = max(deepest, (peak - equity) / peak * PERCENT)
    return deepest
