from dataclasses import dataclass
from uuid import UUID

from autotrading.application.accounts.errors import AccountNameInUseError, AccountNotFoundError
from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.application.verification.errors import VerificationAccountNotFoundError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.verification.verification_access import SealedVerificationAccess


@dataclass(frozen=True, slots=True)
class RemovedAccount:
    """What the database keeps of a removed account: the row the history points to, without credentials."""

    id: AccountId
    tenant_id: TenantId
    name: str
    credentials: None = None


class AccountStore:
    """The accounts of every tenant, as the database holds them."""

    def __init__(self) -> None:
        self.accounts: list[Account] = []
        self.removed: list[RemovedAccount] = []

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

    def list(self) -> list[Account]:
        return self._store.of(self._tenant_id)

    def get(self, account_id: AccountId) -> Account | None:
        return next((account for account in self.list() if account.id == account_id), None)

    def sealed_access(self, account_id: UUID) -> SealedAccess:
        account = self.get(AccountId(account_id))
        if account is None:
            raise OrderAccountNotFoundError
        sealed = account.credentials
        return SealedAccess(
            account.tenant_id, account_id, account.exchange.value, sealed.key_version, sealed.ciphertext
        )

    def sealed_address(self, account_id: UUID) -> SealedAddress:
        account = self.get(AccountId(account_id))
        if account is None:
            raise FlowAccountNotFoundError
        sealed = account.credentials
        return SealedAddress(
            account.tenant_id, account_id, account.exchange.value, sealed.key_version, sealed.ciphertext
        )

    def sealed_verification(self, account_id: UUID) -> SealedVerificationAccess:
        account = self.get(AccountId(account_id))
        if account is None:
            raise VerificationAccountNotFoundError
        sealed = account.credentials
        return SealedVerificationAccess(
            account.tenant_id, account_id, account.exchange.value, sealed.key_version, sealed.ciphertext
        )

    def replace(self, account: Account) -> None:
        current = self.get(account.id)
        if current is None or account.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self._store.accounts[self._store.accounts.index(current)] = account

    def add(self, account: Account) -> None:
        if self._taken_before_next_add is not None:
            self._store.accounts.append(self._taken_before_next_add)
            self._taken_before_next_add = None
        if self.name_in_use(account.name):
            raise AccountNameInUseError(account.name)
        self._store.accounts.append(account)

    def remove(self, account_id: AccountId) -> None:
        account = self.get(account_id)
        if account is None:
            raise AccountNotFoundError
        self._store.accounts.remove(account)
        self._store.removed.append(RemovedAccount(account.id, account.tenant_id, account.name.value))

    def take_name_before_next_add(self, account: Account) -> None:
        """Simulates another request that saves an account with the same name between the check and the insert."""
        self._taken_before_next_add = account
