from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.errors import CycleFlowNotFoundError, CycleNotFoundError
from autotrading.application.flows.ports import CycleHistoryPort, FlowDirectoryPort
from autotrading.domain.flows.cycle_record import CycleRecord


@dataclass(frozen=True, slots=True)
class ReadCycleCommand:
    flow_id: UUID
    planned_at: datetime


class ReadCycleUseCase:
    """A cycle of a flow of the tenant with everything recorded about it (R1.7.1, R1.7.3)."""

    def __init__(self, flows: FlowDirectoryPort, history: CycleHistoryPort) -> None:
        self._flows = flows
        self._history = history

    def execute(self, command: ReadCycleCommand) -> CycleRecord:
        if not self._flows.exists(command.flow_id):
            raise CycleFlowNotFoundError
        record = self._history.at(command.flow_id, command.planned_at)
        if record is None:
            raise CycleNotFoundError
        return record
