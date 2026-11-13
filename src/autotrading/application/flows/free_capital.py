from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.flow_account import read_flow_account
from autotrading.application.flows.ports import FlowAccount, FlowAccountPorts, FlowRepositoryPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.free_capital import FreeCapital


def free_capital_of(account: FlowAccount, account_id: UUID, flows: Iterable[Flow]) -> FreeCapital:
    return FreeCapital.of(account.balance, account.currency, (flow for flow in flows if flow.account_id == account_id))


@dataclass(frozen=True, slots=True)
class ReadFreeCapitalCommand:
    account_id: UUID


class ReadFreeCapitalUseCase:
    """The capital of an account still free for new flows: its balance now, less what its flows hold (R1.1.1)."""

    def __init__(self, flows: FlowRepositoryPort, accounts: FlowAccountPorts) -> None:
        self._flows = flows
        self._accounts = accounts

    def execute(self, command: ReadFreeCapitalCommand) -> FreeCapital:
        account = read_flow_account(self._accounts, command.account_id)
        return free_capital_of(account, command.account_id, self._flows.list())
