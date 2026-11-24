from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from autotrading.application.accounts.errors import VirtualBalanceNotHeldError
from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, VirtualBalancePort
from autotrading.application.accounts.verification import operations
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.virtual_balance import VirtualBalance


@dataclass(frozen=True, slots=True)
class ResetVirtualBalanceCommand:
    account_id: AccountId
    balance: Decimal


class ResetVirtualBalanceUseCase:
    """Starts an account of an exchange with a virtual balance again from the balance the user gives, whenever he wants:
    its positions closed and its orders cancelled first (R6.3.2).

    An account of another tenant is not found (R0.1.3); one of an exchange with real or test funds has no virtual
    balance to reset.
    """

    def __init__(self, accounts: AccountRepositoryPort, virtual_balances: Mapping[str, VirtualBalancePort]) -> None:
        self._accounts = accounts
        self._virtual_balances = virtual_balances

    def execute(self, command: ResetVirtualBalanceCommand) -> None:
        balance = VirtualBalance(command.balance)
        account = find_account(self._accounts, command.account_id)
        virtual_balances = self._virtual_balances.get(account.exchange.value)
        if virtual_balances is None:
            raise VirtualBalanceNotHeldError
        virtual_balances.reset(account.id, balance)
        operations.info("saldo virtuale azzerato", extra={"account_id": str(account.id.value)})
