from dataclasses import dataclass

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountFlowsPort, AccountRepositoryPort, AccountStatePort
from autotrading.application.accounts.verification import operations
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.removal import (
    require_all_closed,
    require_confirmation_for,
    require_confirmation_for_flows,
)
from autotrading.domain.tenancy.user_id import UserId


@dataclass(frozen=True, slots=True)
class RemoveAccountCommand:
    account_id: AccountId
    # Who removes the account: the closing orders of its flows are recorded as theirs (R1.1.8).
    user_id: UserId
    # The user accepts that open positions stay on the exchange without management (R0.2.5), and that the flows
    # operating on the account are stopped with their positions closed (R1.1.8).
    confirmed: bool = False


class RemoveAccountUseCase:
    """Removes an account of the tenant: its credentials are deleted, its history stays (R0.2.5, ADR 0025).

    Without confirmation the flows and then the positions are checked first, and an account with flows operating or
    positions open is not removed. With confirmation the flows of the account are stopped closing their positions:
    a position left open keeps the account, otherwise it is removed and its flows archived (R1.1.8, ADR 0054).
    """

    def __init__(
        self, accounts: AccountRepositoryPort, account_state: AccountStatePort, flows: AccountFlowsPort
    ) -> None:
        self._accounts = accounts
        self._account_state = account_state
        self._flows = flows

    def execute(self, command: RemoveAccountCommand) -> None:
        account = find_account(self._accounts, command.account_id)
        if not command.confirmed:
            require_confirmation_for_flows(self._flows.operating(account.id))
            require_confirmation_for(self._account_state.read_state(account.id).positions)
        require_all_closed(self._flows.stop(account.id, command.user_id))
        self._accounts.remove(account.id)
        self._flows.archive(account.id)
        operations.info("conto rimosso", extra={"account_id": str(account.id.value)})
