from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.ports import CycleHistoryPort, FlowDirectoryPort
from autotrading.domain.flows.cycle_page import CYCLES_PER_PAGE, CyclePage
from autotrading.domain.flows.page_number import PageNumber


@dataclass(frozen=True, slots=True)
class ListCyclesCommand:
    flow_id: UUID
    page: int = 1


class ListCyclesUseCase:
    """The cycles of a flow of the tenant, from the most recent, in pages of 50 (R1.7.3)."""

    def __init__(self, flows: FlowDirectoryPort, history: CycleHistoryPort) -> None:
        self._flows = flows
        self._history = history

    def execute(self, command: ListCyclesCommand) -> CyclePage:
        number = PageNumber(command.page)
        if not self._flows.exists(command.flow_id):
            raise CycleFlowNotFoundError
        # One cycle more than the page tells whether another page follows.
        found = self._history.newest(command.flow_id, number.offset(CYCLES_PER_PAGE), CYCLES_PER_PAGE + 1)
        return CyclePage(number.value, tuple(found[:CYCLES_PER_PAGE]), len(found) > CYCLES_PER_PAGE)
