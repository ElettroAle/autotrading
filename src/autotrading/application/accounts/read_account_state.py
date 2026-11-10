from dataclasses import dataclass

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, AccountStatePort
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState


@dataclass(frozen=True, slots=True)
class ReadAccountStateCommand:
    account_id: AccountId


class ReadAccountStateUseCase:
    """The live state of an account of the tenant, read by the worker that holds the private key (R0.2.2, ADR 0021).

    The account is looked up here first, so an account of another tenant never leaves the API (R0.1.3).
    """

    def __init__(self, accounts: AccountRepositoryPort, account_state: AccountStatePort) -> None:
        self._accounts = accounts
        self._account_state = account_state

    def execute(self, command: ReadAccountStateCommand) -> AccountState:
        account = find_account(self._accounts, command.account_id)
        return self._account_state.read_state(account.id)
