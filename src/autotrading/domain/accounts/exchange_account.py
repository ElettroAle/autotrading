import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials


@dataclass(frozen=True, slots=True)
class ExchangeAccount:
    """Which account on the exchange some credentials operate, kept as a digest of their public fields.

    The API cannot open sealed credentials, yet it must refuse credentials of another exchange account (R0.2.4);
    the digest answers that question without keeping the account in clear (R0.2.3, ADR 0019). The public fields
    are the ones the exchange does not declare secret (ADR 0158).
    """

    fingerprint: str

    @classmethod
    def of(cls, credentials: Credentials, fields: Iterable[CredentialField]) -> ExchangeAccount:
        public = "\n".join(
            credentials.value(credential_field.name).lower()
            for credential_field in fields
            if not credential_field.secret
        )
        return cls(hashlib.sha256(public.encode()).hexdigest())
