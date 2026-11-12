from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import ClosedPositionRepositoryPort, FlowRepositoryPort
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class ListClosedPositionsCommand:
    flow_id: UUID


class ListClosedPositionsUseCase:
    """The closed positions of a flow of the tenant, from the most recent close (R1.7.2)."""

    def __init__(self, flows: FlowRepositoryPort, positions: ClosedPositionRepositoryPort) -> None:
        self._flows = flows
        self._positions = positions

    def execute(self, command: ListClosedPositionsCommand) -> list[ClosedPosition]:
        flow = self._flows.get(FlowId(command.flow_id))
        return sorted(self._positions.of_flow(flow.id), key=lambda position: position.closing.at, reverse=True)
