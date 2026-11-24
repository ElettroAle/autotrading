"""Accounts built directly, for tests that need one already saved without going through the registration."""

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.credentials import HYPERLIQUID_FIELDS, hyperliquid_credentials

ADDRESS = "0x1111111111111111111111111111111111111111"
SECRET = "0x" + "ab" * 32


def an_account(
    tenant_id: TenantId,
    name: str = "test-1",
    sealed: SealedCredentials | None = None,
    credentials: Credentials | None = None,
) -> Account:
    return Account(
        AccountId.new(),
        tenant_id,
        AccountName(name),
        ExchangeName("Hyperliquid"),
        ExchangeAccount.of(credentials or hyperliquid_credentials(ADDRESS, SECRET), HYPERLIQUID_FIELDS),
        sealed or SealedCredentials(1, b"sealed"),
    )


SIMULATED = "simulato"


def a_simulated_account(tenant_id: TenantId, name: str = "simulato-1") -> Account:
    """An account of the simulated exchange: no credentials, nothing sealed (R6.3.2)."""
    account_id = AccountId.new()
    return Account(
        account_id,
        tenant_id,
        AccountName(name),
        ExchangeName(SIMULATED),
        ExchangeAccount.of(Credentials.without_fields(account_id), ()),
        SealedCredentials.none(),
    )
