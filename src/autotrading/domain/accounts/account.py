from dataclasses import dataclass, replace

from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.errors import CredentialsOfAnotherAccountError
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned


@dataclass(frozen=True, slots=True)
class Account(TenantOwned):
    """A trading account on an exchange, owned by a tenant. Its credentials are only ever stored sealed."""

    id: AccountId
    tenant_id: TenantId
    name: AccountName
    exchange: ExchangeName
    exchange_account: ExchangeAccount
    credentials: SealedCredentials

    def require_same_exchange_account(self, credentials: Credentials) -> None:
        """New credentials must operate the same account on the exchange (R0.2.4)."""
        if ExchangeAccount.of(credentials) != self.exchange_account:
            raise CredentialsOfAnotherAccountError

    def with_credentials(self, sealed: SealedCredentials) -> Account:
        # The previous sealed text is gone from the account: nothing keeps the replaced credentials (R0.2.4).
        return replace(self, credentials=sealed)
