import hashlib
from dataclasses import dataclass

from autotrading.domain.accounts.credentials import Credentials


@dataclass(frozen=True, slots=True)
class ExchangeAccount:
    """Which account on the exchange some credentials operate, kept as a digest of its address.

    The API cannot open sealed credentials, yet it must refuse credentials of another exchange account (R0.2.4);
    the digest answers that question without keeping the address in clear (R0.2.3, ADR 0019).
    """

    fingerprint: str

    @classmethod
    def of(cls, credentials: Credentials) -> ExchangeAccount:
        address = credentials.account_address.lower().encode()
        return cls(hashlib.sha256(address).hexdigest())
