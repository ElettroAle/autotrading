from dataclasses import dataclass, field
from uuid import UUID

from autotrading.application.flows.ports import AccountTransfersPort, FlowRepositoryPort
from autotrading.domain.flows.capital_history import CapitalHistoryEntry, CapitalHistoryPage, entries_to_read
from autotrading.domain.flows.page_number import PageNumber
from autotrading.domain.flows.statistics_period import TimeWindow


@dataclass(frozen=True, slots=True)
class ListAccountCapitalChangesCommand:
    account_id: UUID
    page: int = 1
    window: TimeWindow = field(default_factory=TimeWindow)


class ListAccountCapitalChangesUseCase:
    """The history of the capital of an account in a period: the changes of every one of its flows and the deposits
    and withdrawals its exchange declares, from the most recent, in pages of 50 (R3.4.2, ADR
    storico-delle-variazioni-di-capitale).

    The transfers are read first: an exchange that cannot be read gives no history, never a part of it.
    """

    def __init__(self, flows: FlowRepositoryPort, transfers: AccountTransfersPort, currency: str) -> None:
        self._flows = flows
        self._transfers = transfers
        self._currency = currency

    def execute(self, command: ListAccountCapitalChangesCommand) -> CapitalHistoryPage:
        number = PageNumber(command.page)
        transfers = self._transfers.transfers(command.account_id, command.window)
        names = {flow.id: flow.name.value for flow in self._flows.list() if flow.account_id == command.account_id}
        changes = self._flows.capital_changes(names, command.window, entries_to_read(number))
        total = self._flows.count_capital_changes(names, command.window) + len(transfers)
        entries = [
            *(CapitalHistoryEntry.of_change(change, names[change.flow_id]) for change in changes),
            *(CapitalHistoryEntry.of_transfer(transfer) for transfer in transfers),
        ]
        return CapitalHistoryPage.of(number, entries, total, self._currency)
