from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.flow_account import read_free_capital
from autotrading.application.flows.ports import FlowAccountPorts, FlowRepositoryPort
from autotrading.domain.flows.free_capital import FreeCapital


@dataclass(frozen=True, slots=True)
class ReadFreeCapitalCommand:
    account_id: UUID


class ReadFreeCapitalUseCase:
    """The capital of an account still free for new flows: its balance now, less the total value of its flows (R1.1.1,
    ADR capitale-libero-al-netto-del-valore-dei-flussi). An account the tenant lacks is not found before it is read.
    """

    def __init__(self, flows: FlowRepositoryPort, accounts: FlowAccountPorts) -> None:
        self._flows = flows
        self._accounts = accounts

    def execute(self, command: ReadFreeCapitalCommand) -> FreeCapital:
        self._accounts.directory.exchange_of(command.account_id)
        return read_free_capital(self._flows, self._accounts, command.account_id)
