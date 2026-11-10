from dataclasses import dataclass

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, AccountStatePort
from autotrading.application.accounts.verification import operations
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.removal import require_confirmation_for


@dataclass(frozen=True, slots=True)
class RemoveAccountCommand:
    account_id: AccountId
    # The user accepts that open positions stay on the exchange without management (R0.2.5).
    confirmed: bool = False


class RemoveAccountUseCase:
    """Removes an account of the tenant: its credentials are deleted, its history stays (R0.2.5, ADR 0025).

    Without confirmation the positions are read first, and an account with open positions is not removed. With
    confirmation nothing is read: the removal works also with credentials the exchange no longer accepts.
    """

    def __init__(self, accounts: AccountRepositoryPort, account_state: AccountStatePort) -> None:
        self._accounts = accounts
        self._account_state = account_state

    def execute(self, command: RemoveAccountCommand) -> None:
        account = find_account(self._accounts, command.account_id)
        if not command.confirmed:
            require_confirmation_for(self._account_state.read_state(account.id).positions)
        self._accounts.remove(account.id)
        operations.info("conto rimosso", extra={"account_id": str(account.id.value)})
