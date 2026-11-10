"""The platform as the scenarios see it: the use cases of a tenant built on the fake adapters, as bootstrap does."""

from secrets import token_hex

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.accounts.register_account import AccountRegistration, RegisterAccountCommand
from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.account_state import FakeAccountStateAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter, SealedVault
from tests.fakes.exchange import FakeExchangeAdapter
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.directory import Directory

HYPERLIQUID = "Hyperliquid"


def new_credentials() -> Credentials:
    return Credentials(account_address=f"0x{token_hex(20)}", secret_key=f"0x{token_hex(32)}")


class Platform:
    def __init__(self) -> None:
        self.directory = Directory()
        self.tenants = InMemoryTenantRepositoryAdapter()
        self.accounts = AccountStore()
        self.exchanges = {HYPERLIQUID: FakeExchangeAdapter()}
        self.vault: SealedVault = {}
        self.worker_reachable = True

    @property
    def hyperliquid(self) -> FakeExchangeAdapter:
        return self.exchanges[HYPERLIQUID]

    def tenant_of(self, user: str) -> TenantId:
        command = ResolveTenantCommand(UserId(self.directory.person(user).object_id))
        return ResolveTenantUseCase(self.tenants).execute(command)

    def accounts_of(self, user: str) -> list[Account]:
        return self.accounts.of(self.tenant_of(user))

    def accepted_credentials(self) -> Credentials:
        credentials = new_credentials()
        self.hyperliquid.accept(credentials)
        return credentials

    def register_account(self, user: str, command: RegisterAccountCommand) -> AccountRegistration:
        return self.use_cases_of(user).register_account.execute(command)

    def for_tenant(self, tenant_id: TenantId) -> TenantUseCases:
        """What bootstrap.for_tenant does, on the fake adapters."""
        accounts = InMemoryAccountRepositoryAdapter(self.accounts, tenant_id)
        account_state = FakeAccountStateAdapter(lambda: self.worker_for(tenant_id))
        account_state.reachable = self.worker_reachable
        return TenantUseCases.on(tenant_id, accounts, self.sealer_of(tenant_id), self.exchanges, account_state)

    def worker_for(self, tenant_id: TenantId) -> ReadExchangeStateUseCase:
        """What the worker builds for a request of the API, with the opener only it holds."""
        accounts = InMemoryAccountRepositoryAdapter(self.accounts, tenant_id)
        return ReadExchangeStateUseCase(accounts, FakeCredentialOpenerAdapter(self.vault), self.exchanges)

    def use_cases_of(self, user: str) -> TenantUseCases:
        return self.for_tenant(self.tenant_of(user))

    def sealer_of(self, tenant_id: TenantId) -> FakeCredentialSealerAdapter:
        return FakeCredentialSealerAdapter(tenant_id, self.vault)

    def uses_credentials(self, account: Account, credentials: Credentials) -> bool:
        """The fake seal is deterministic: sealing the same credentials again gives the saved text."""
        return account.credentials == self.sealer_of(account.tenant_id).seal(account.id, credentials)

    def account_named(self, user: str, name: str) -> Account:
        return next(account for account in self.accounts_of(user) if account.name.value == name)


def registration(name: str, exchange: str, credentials: Credentials) -> RegisterAccountCommand:
    return RegisterAccountCommand(name, exchange, credentials.account_address, credentials.secret_key)
