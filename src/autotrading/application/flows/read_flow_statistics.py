from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from autotrading.application.flows.ports import ClosedPositionRepositoryPort, CycleHistoryPort, FlowRepositoryPort
from autotrading.domain.flows.flow_cost import FlowCost
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_statistics import FlowStatistics
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind


@dataclass(frozen=True, slots=True)
class ReadFlowStatisticsCommand:
    flow_id: UUID
    period: str = StatisticsPeriodKind.ALL.value
    first_day: date | None = None
    last_day: date | None = None


class ReadFlowStatisticsUseCase:
    """The statistics of a flow of the tenant over a period, from its closed positions and its model calls (R2.2.6)."""

    def __init__(
        self,
        flows: FlowRepositoryPort,
        positions: ClosedPositionRepositoryPort,
        history: CycleHistoryPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._flows = flows
        self._positions = positions
        self._history = history
        self._clock = clock

    def execute(self, command: ReadFlowStatisticsCommand) -> FlowStatistics:
        period = StatisticsPeriod.named(command.period, command.first_day, command.last_day)
        flow = self._flows.get(FlowId(command.flow_id))
        window = period.window(self._clock())
        positions = self._positions.closed_within(flow.id, window)
        cost = FlowCost.of(self._history.costs_within(flow.id.value, window))
        return FlowStatistics.of(positions, cost)
