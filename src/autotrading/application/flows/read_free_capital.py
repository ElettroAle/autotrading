from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowAccountPort, FlowRepositoryPort
from autotrading.domain.flows.free_capital import FreeCapital


@dataclass(frozen=True, slots=True)
class ReadFreeCapitalCommand:
    account_id: UUID


class ReadFreeCapitalUseCase:
    """The capital of an account still free for new flows: its balance now, less what its flows hold (R1.1.1)."""

    def __init__(self, flows: FlowRepositoryPort, accounts: FlowAccountPort) -> None:
        self._flows = flows
        self._accounts = accounts

    def execute(self, command: ReadFreeCapitalCommand) -> FreeCapital:
        account = self._accounts.account(command.account_id)
        return FreeCapital.of_account(account.balance, account.currency, command.account_id, self._flows.list())
