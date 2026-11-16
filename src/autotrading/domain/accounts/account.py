from dataclasses import dataclass, field, replace

from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
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
    deviation_threshold: DeviationThreshold = field(default_factory=DeviationThreshold.default)

    def require_same_exchange_account(self, exchange_account: ExchangeAccount) -> None:
        """New credentials must operate the same account on the exchange (R0.2.4)."""
        if exchange_account != self.exchange_account:
            raise CredentialsOfAnotherAccountError

    def with_exchange_account(self, exchange_account: ExchangeAccount) -> Account:
        """The same exchange account with its public fields as the credentials just accepted declare them (Bug 401)."""
        self.require_same_exchange_account(exchange_account)
        return replace(self, exchange_account=exchange_account)

    def with_credentials(self, sealed: SealedCredentials) -> Account:
        # The previous sealed text is gone from the account: nothing keeps the replaced credentials (R0.2.4).
        return replace(self, credentials=sealed)

    def with_deviation_threshold(self, threshold: DeviationThreshold) -> Account:
        """The deviation of the balance beyond which the reconciliation raises an alarm on the account (R3.3.1)."""
        return replace(self, deviation_threshold=threshold)
