from dataclasses import dataclass, field, replace
from decimal import Decimal

from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.accounts.errors import CredentialsOfAnotherAccountError, MaxDirectionExposureNotPositiveError
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.key_expiry import KeyExpiry
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
    # None while the expiry of the credentials is unknown (R6.2.2).
    expiry: KeyExpiry | None = None
    # None unless the user sets it: the flows of the account open on a side whatever the others hold (R5.5.5).
    max_direction_exposure_percent: Decimal | None = None

    def __post_init__(self) -> None:
        percent = self.max_direction_exposure_percent
        if percent is not None and not (percent.is_finite() and percent > 0):
            raise MaxDirectionExposureNotPositiveError(percent)

    def require_same_exchange_account(self, exchange_account: ExchangeAccount) -> None:
        """New credentials must operate the same account on the exchange (R0.2.4)."""
        if exchange_account != self.exchange_account:
            raise CredentialsOfAnotherAccountError

    def with_exchange_account(self, exchange_account: ExchangeAccount) -> Account:
        """The same exchange account with its public fields as the credentials just accepted declare them (Bug 401)."""
        self.require_same_exchange_account(exchange_account)
        return replace(self, exchange_account=exchange_account)

    def with_credentials(self, sealed: SealedCredentials) -> Account:
        """The previous sealed text is gone from the account: nothing keeps the replaced credentials (R0.2.4); nor
        the date the user gave for them, which was the expiry of the replaced ones (R6.2.2)."""
        expiry = None if self.expiry is not None and self.expiry.was_entered else self.expiry
        return replace(self, credentials=sealed, expiry=expiry)

    def with_expiry(self, expiry: KeyExpiry | None) -> Account:
        """The day the credentials stop working, read by the adapter of the exchange or given by the user (R6.2.2)."""
        return replace(self, expiry=expiry)

    def with_deviation_threshold(self, threshold: DeviationThreshold) -> Account:
        """The deviation of the balance beyond which the reconciliation raises an alarm on the account (R3.3.1)."""
        return replace(self, deviation_threshold=threshold)

    def with_max_direction_exposure(self, percent: Decimal | None) -> Account:
        """The largest exposure the flows of the account may have together on one side, in percent of its balance read
        from the exchange; None takes the limit away (R5.5.5, ADR esposizione-massima-per-direzione-del-conto)."""
        return replace(self, max_direction_exposure_percent=percent)
