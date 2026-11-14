from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import EquitySnapshotRepositoryPort, FlowRepositoryPort
from autotrading.domain.flows.equity_period import EquityPeriod
from autotrading.domain.flows.equity_snapshot import FlowEquity
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class ReadFlowEquityCommand:
    """The flow and the period of its curve; a range needs its start, included, and its end, excluded."""

    flow_id: UUID
    period: EquityPeriod = EquityPeriod.LIFETIME
    start: datetime | None = None
    end: datetime | None = None


class ReadFlowEquityUseCase:
    """The equity curve of a flow of the tenant in the period the user chooses: a point for each cycle (R2.2.3)."""

    def __init__(
        self, flows: FlowRepositoryPort, equity: EquitySnapshotRepositoryPort, clock: Callable[[], datetime]
    ) -> None:
        self._flows = flows
        self._equity = equity
        self._clock = clock

    def execute(self, command: ReadFlowEquityCommand) -> FlowEquity:
        window = command.period.window(self._clock(), command.start, command.end)
        flow = self._flows.get(FlowId(command.flow_id))
        snapshots = self._equity.of_flow(flow.id.value, window)
        return FlowEquity(flow.configuration.allocated_capital, tuple(snapshots))
