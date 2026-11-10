"""The platform as the scenarios see it: the use cases of a tenant built on the fake adapters, as bootstrap does."""

from secrets import token_hex

from autotrading.application.accounts.register_account import (
    AccountRegistration,
    RegisterAccountCommand,
    RegisterAccountUseCase,
)
from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter
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
        return self.register_account_use_case(user).execute(command)

    def register_account_use_case(self, user: str) -> RegisterAccountUseCase:
        tenant_id = self.tenant_of(user)
        return RegisterAccountUseCase(
            tenant_id,
            InMemoryAccountRepositoryAdapter(self.accounts, tenant_id),
            FakeCredentialSealerAdapter(tenant_id),
            self.exchanges,
        )


def registration(name: str, exchange: str, credentials: Credentials) -> RegisterAccountCommand:
    return RegisterAccountCommand(name, exchange, credentials.account_address, credentials.secret_key)
