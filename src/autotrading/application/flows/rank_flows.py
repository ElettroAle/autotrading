from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    CycleHistoryPort,
    EquitySnapshotRepositoryPort,
    FlowRepositoryPort,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_cost import FlowCost
from autotrading.domain.flows.flow_ranking import FlowRanking, ranked_by_return
from autotrading.domain.flows.flow_statistics import FlowStatistics
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind, TimeWindow


@dataclass(frozen=True, slots=True)
class RankFlowsCommand:
    """The period of the ranking, the same periods as the statistics (ADR 0122)."""

    period: str = StatisticsPeriodKind.ALL.value
    since: datetime | None = None
    until: datetime | None = None


# A draft has never run and an archived flow is over: neither competes with the flows at work.
_OUT_OF_RANKING = frozenset({FlowStatus.DRAFT, FlowStatus.ARCHIVED})


class RankFlowsUseCase:
    """The ranking of the flows of the tenant neither drafts nor archived with a cycle in the period, from the highest
    return compounded across the changes of the capital (R2.4.2, ADR 0135, R3.4.3).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        equity: EquitySnapshotRepositoryPort,
        positions: ClosedPositionRepositoryPort,
        history: CycleHistoryPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._flows = flows
        self._equity = equity
        self._positions = positions
        self._history = history
        self._clock = clock

    def execute(self, command: RankFlowsCommand) -> tuple[FlowRanking, ...]:
        period = StatisticsPeriod.named(command.period, command.since, command.until)
        now = self._clock()
        return ranked_by_return(self._rankings(period.window(now), now))

    def _rankings(self, window: TimeWindow, now: datetime) -> Iterator[FlowRanking]:
        for flow in self._flows.list():
            if flow.status in _OUT_OF_RANKING:
                continue
            snapshots = self._equity.of_flow(flow.id.value, window.ending_by(now))
            if not snapshots:
                continue
            changes = self._flows.capital_changes_of((flow.id,)).get(flow.id, ())
            statistics = self._statistics(flow, window)
            yield FlowRanking.of(flow.id.value, flow.name.value, snapshots, statistics, changes)

    def _statistics(self, flow: Flow, window: TimeWindow) -> FlowStatistics:
        positions = self._positions.closed_within(flow.id, window)
        cost = FlowCost.of(self._history.costs_within(flow.id.value, window))
        return FlowStatistics.of(positions, cost)
