from dataclasses import dataclass
from datetime import date

from autotrading.application.accounts.ports import ExchangePort
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.key_expiry import KeyExpiry, KeyExpiryReading, expiry_reading_of


@dataclass(frozen=True, slots=True)
class KeyExpiryDetails:
    """What a user reads of the expiry of the credentials of an account on a day: the date and who gave it, its state
    with the days left, and whether the user may give the date, which only an exchange that does not read it allows
    (R6.2.2, ADR scadenza-delle-chiavi-letta-o-indicata).
    """

    expiry: KeyExpiry | None
    reading: KeyExpiryReading
    editable: bool

    @classmethod
    def of(cls, account: Account, exchange: ExchangePort, today: date) -> KeyExpiryDetails:
        return cls(account.expiry, expiry_reading_of(account.expiry, today), not exchange.reads_credential_expiry())
