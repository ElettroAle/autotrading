from dataclasses import dataclass, field
from uuid import UUID

from autotrading.application.flows.ports import ClosedPositionRepositoryPort, FlowRepositoryPort
from autotrading.domain.flows.closed_position_filter import ClosedPositionFilter
from autotrading.domain.flows.closed_position_page import CLOSED_POSITIONS_PER_PAGE, ClosedPositionPage
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.page_number import PageNumber


@dataclass(frozen=True, slots=True)
class ListClosedPositionsCommand:
    flow_id: UUID
    page: int = 1
    criteria: ClosedPositionFilter = field(default_factory=ClosedPositionFilter)


class ListClosedPositionsUseCase:
    """The closed positions of a flow of the tenant that match the filter, from the most recent close, in pages of 50,
    with how many match in all (R1.7.2, R2.2.5, R6.4.4).
    """

    def __init__(self, flows: FlowRepositoryPort, positions: ClosedPositionRepositoryPort) -> None:
        self._flows = flows
        self._positions = positions

    def execute(self, command: ListClosedPositionsCommand) -> ClosedPositionPage:
        number = PageNumber(command.page)
        flow = self._flows.get(FlowId(command.flow_id))
        # One position more than the page tells whether another page follows.
        found = self._positions.matching(
            flow.id, command.criteria, number.offset(CLOSED_POSITIONS_PER_PAGE), CLOSED_POSITIONS_PER_PAGE + 1
        )
        total = self._positions.count(flow.id, command.criteria)
        return ClosedPositionPage(
            number.value, tuple(found[:CLOSED_POSITIONS_PER_PAGE]), len(found) > CLOSED_POSITIONS_PER_PAGE, total
        )
