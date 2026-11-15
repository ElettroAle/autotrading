from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_name import ExchangeName


@dataclass(frozen=True, slots=True)
class AccountDetails:
    """What a user reads of an account: whether credentials are present, never the secret ones (R0.2.3), and the
    public fields kept, which name the account on the exchange (Bug 401)."""

    id: AccountId
    name: AccountName
    exchange: ExchangeName
    has_credentials: bool
    public_fields: Mapping[str, str]

    @classmethod
    def of(cls, account: Account) -> AccountDetails:
        return cls(
            account.id,
            account.name,
            account.exchange,
            has_credentials=bool(account.credentials.ciphertext),
            public_fields=public_fields_of(account),
        )


def public_fields_of(account: Account) -> Mapping[str, str]:
    """None kept, for an account registered before they were: nothing to show."""
    return dict(account.exchange_account.public_fields or {})
