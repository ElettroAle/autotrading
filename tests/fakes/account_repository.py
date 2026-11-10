from autotrading.application.accounts.errors import AccountNameInUseError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.tenancy.tenant_id import TenantId


class AccountStore:
    """The accounts of every tenant, as the database holds them."""

    def __init__(self) -> None:
        self.accounts: list[Account] = []

    def of(self, tenant_id: TenantId) -> list[Account]:
        return [account for account in self.accounts if account.tenant_id == tenant_id]


class InMemoryAccountRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security."""

    def __init__(self, store: AccountStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id
        self._taken_before_next_add: Account | None = None

    def name_in_use(self, name: AccountName) -> bool:
        return any(account.name == name for account in self._store.of(self._tenant_id))

    def add(self, account: Account) -> None:
        if self._taken_before_next_add is not None:
            self._store.accounts.append(self._taken_before_next_add)
            self._taken_before_next_add = None
        if self.name_in_use(account.name):
            raise AccountNameInUseError(account.name)
        self._store.accounts.append(account)

    def take_name_before_next_add(self, account: Account) -> None:
        """Simulates another request that saves an account with the same name between the check and the insert."""
        self._taken_before_next_add = account
