from dataclasses import dataclass

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_name import ExchangeName


@dataclass(frozen=True, slots=True)
class AccountDetails:
    """What a user reads of an account: whether credentials are present, never the credentials (R0.2.3)."""

    id: AccountId
    name: AccountName
    exchange: ExchangeName
    has_credentials: bool

    @classmethod
    def of(cls, account: Account) -> AccountDetails:
        return cls(account.id, account.name, account.exchange, has_credentials=bool(account.credentials.ciphertext))
