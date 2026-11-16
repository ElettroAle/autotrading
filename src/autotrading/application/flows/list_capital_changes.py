from dataclasses import dataclass, field

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.capital_history import CapitalHistoryEntry, CapitalHistoryPage, entries_to_read
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.page_number import PageNumber
from autotrading.domain.flows.statistics_period import TimeWindow


@dataclass(frozen=True, slots=True)
class ListCapitalChangesCommand:
    flow_id: FlowId
    page: int = 1
    window: TimeWindow = field(default_factory=TimeWindow)


class ListCapitalChangesUseCase:
    """The history of the capital of a flow in a period, from the most recent change, in pages of 50 (R1.1.7, R3.4.2,
    ADR storico-delle-variazioni-di-capitale)."""

    def __init__(self, flows: FlowRepositoryPort, currency: str) -> None:
        self._flows = flows
        self._currency = currency

    def execute(self, command: ListCapitalChangesCommand) -> CapitalHistoryPage:
        number = PageNumber(command.page)
        flow = self._flows.get(command.flow_id)
        changes = self._flows.capital_changes((flow.id,), command.window, entries_to_read(number))
        total = self._flows.count_capital_changes((flow.id,), command.window)
        entries = (CapitalHistoryEntry.of_change(change, flow.name.value) for change in changes)
        return CapitalHistoryPage.of(number, entries, total, self._currency)
