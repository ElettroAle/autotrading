from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from autotrading.application.flows.ports import CycleHistoryPort, EquitySnapshotRepositoryPort
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_results import FlowResults
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind


@dataclass(frozen=True, slots=True)
class ReadFlowResultsCommand:
    """The flow and the period of its results, the same periods as the statistics (ADR 0122)."""

    flow_id: UUID
    period: str = StatisticsPeriodKind.ALL.value
    first_day: date | None = None
    last_day: date | None = None


class ReadFlowResultsUseCase:
    """How a flow of the tenant is doing at a glance in the period the user chooses: its state read now, the equity its
    cycles recorded in the period and its failed cycles in the period (R6.4.2, ADR riepilogo-dei-risultati-nell-api).
    """

    def __init__(
        self,
        flow_state: ReadFlowStateUseCase,
        equity: EquitySnapshotRepositoryPort,
        history: CycleHistoryPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._flow_state = flow_state
        self._equity = equity
        self._history = history
        self._clock = clock

    def execute(self, command: ReadFlowResultsCommand) -> FlowResults:
        period = StatisticsPeriod.named(command.period, command.first_day, command.last_day)
        window = period.window(self._clock())
        state = self._flow_state.execute(ReadFlowStateCommand(FlowId(command.flow_id)))
        snapshots = self._equity.of_flow(command.flow_id, window)
        failed_cycles = self._history.failed_within(command.flow_id, window)
        return FlowResults.of(state, snapshots, failed_cycles)
