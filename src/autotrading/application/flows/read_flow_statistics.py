from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    CycleHistoryPort,
    EquitySnapshotRepositoryPort,
    FlowRepositoryPort,
)
from autotrading.domain.flows.flow_cost import FlowCost
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_statistics import FlowStatistics
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind


@dataclass(frozen=True, slots=True)
class ReadFlowStatisticsCommand:
    flow_id: UUID
    period: str = StatisticsPeriodKind.ALL.value
    since: datetime | None = None
    until: datetime | None = None


class ReadFlowStatisticsUseCase:
    """The statistics of a flow of the tenant over a period, from its closed positions, its model calls and the values
    it recorded with the changes of its capital (R2.2.6, ADR rendimento-del-periodo-nelle-statistiche).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        positions: ClosedPositionRepositoryPort,
        history: CycleHistoryPort,
        equity: EquitySnapshotRepositoryPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._flows = flows
        self._positions = positions
        self._history = history
        self._equity = equity
        self._clock = clock

    def execute(self, command: ReadFlowStatisticsCommand) -> FlowStatistics:
        period = StatisticsPeriod.named(command.period, command.since, command.until)
        flow = self._flows.get(FlowId(command.flow_id))
        now = self._clock()
        window = period.window(now)
        positions = self._positions.closed_within(flow.id, window)
        cost = FlowCost.of(self._history.costs_within(flow.id.value, window))
        values = self._equity.of_flow(flow.id.value, window.ending_by(now))
        changes = self._flows.capital_changes_of((flow.id,)).get(flow.id, ())
        return FlowStatistics.of(positions, cost, values, changes)
