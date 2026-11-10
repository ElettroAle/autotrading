from dataclasses import dataclass

from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
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
    credentials: SealedCredentials
