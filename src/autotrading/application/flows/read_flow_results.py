from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import CycleHistoryPort, EquitySnapshotRepositoryPort
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.application.flows.read_next_cycle import ReadNextCycleCommand, ReadNextCycleUseCase
from autotrading.application.flows.read_openings_suspension import (
    ReadOpeningsSuspensionCommand,
    ReadOpeningsSuspensionUseCase,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_results import FlowResults
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind


@dataclass(frozen=True, slots=True)
class ReadFlowResultsCommand:
    """The flow and the period of its results, the same periods as the statistics (ADR 0122)."""

    flow_id: UUID
    period: str = StatisticsPeriodKind.ALL.value
    since: datetime | None = None
    until: datetime | None = None


@dataclass(frozen=True, slots=True)
class FlowPeriodPorts:
    """What a flow recorded in a period: the equity its cycles recorded and its cycles (R6.4.2)."""

    equity: EquitySnapshotRepositoryPort
    history: CycleHistoryPort


class ReadFlowResultsUseCase:
    """How a flow of the tenant is doing at a glance in the period the user chooses: its state read now, the equity its
    cycles recorded in the period and its failed cycles in the period (R6.4.2, ADR riepilogo-dei-risultati-nell-api),
    with why its openings are suspended, if they are (R3.3.2), and when its next cycle falls (R6.4.8, ADR
    prossima-esecuzione-nel-riepilogo-del-flusso).
    """

    def __init__(
        self,
        flow_state: ReadFlowStateUseCase,
        openings_suspension: ReadOpeningsSuspensionUseCase,
        next_cycle: ReadNextCycleUseCase,
        recorded: FlowPeriodPorts,
        clock: Callable[[], datetime],
    ) -> None:
        self._flow_state = flow_state
        self._openings_suspension = openings_suspension
        self._next_cycle = next_cycle
        self._recorded = recorded
        self._clock = clock

    def execute(self, command: ReadFlowResultsCommand) -> FlowResults:
        period = StatisticsPeriod.named(command.period, command.since, command.until)
        window = period.window(self._clock())
        flow_id = FlowId(command.flow_id)
        state = self._flow_state.execute(ReadFlowStateCommand(flow_id))
        snapshots = self._recorded.equity.of_flow(command.flow_id, window)
        failed_cycles = self._recorded.history.failed_within(command.flow_id, window)
        suspension = self._openings_suspension.execute(ReadOpeningsSuspensionCommand(flow_id))
        next_cycle_at = self._next_cycle.execute(ReadNextCycleCommand(flow_id))
        return FlowResults.of(state, snapshots, failed_cycles, suspension, next_cycle_at)
