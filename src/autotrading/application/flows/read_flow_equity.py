from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from autotrading.application.flows.ports import EquitySnapshotRepositoryPort, FlowRepositoryPort
from autotrading.domain.flows.equity_snapshot import FlowEquity
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind


@dataclass(frozen=True, slots=True)
class ReadFlowEquityCommand:
    """The flow and the period of its curve, the same periods as the statistics (ADR 0122)."""

    flow_id: UUID
    period: str = StatisticsPeriodKind.ALL.value
    first_day: date | None = None
    last_day: date | None = None


class ReadFlowEquityUseCase:
    """The equity curve of a flow of the tenant in the period the user chooses: a point for each cycle (R2.2.3)."""

    def __init__(
        self, flows: FlowRepositoryPort, equity: EquitySnapshotRepositoryPort, clock: Callable[[], datetime]
    ) -> None:
        self._flows = flows
        self._equity = equity
        self._clock = clock

    def execute(self, command: ReadFlowEquityCommand) -> FlowEquity:
        period = StatisticsPeriod.named(command.period, command.first_day, command.last_day)
        flow = self._flows.get(FlowId(command.flow_id))
        snapshots = self._equity.of_flow(flow.id.value, period.window(self._clock()))
        return FlowEquity(flow.configuration.allocated_capital, tuple(snapshots))
