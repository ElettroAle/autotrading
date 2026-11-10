"""Accounts built directly, for tests that need one already saved without going through the registration."""

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId

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
        ExchangeAccount.of(credentials or Credentials(ADDRESS, SECRET)),
        sealed or SealedCredentials(1, b"sealed"),
    )
