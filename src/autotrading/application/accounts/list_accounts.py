from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.ports import AccountRepositoryPort


class ListAccountsUseCase:
    """The accounts of the tenant of the request, and only those (R0.1.3)."""

    def __init__(self, accounts: AccountRepositoryPort) -> None:
        self._accounts = accounts

    def execute(self) -> list[AccountDetails]:
        return [AccountDetails.of(account) for account in self._accounts.list()]
