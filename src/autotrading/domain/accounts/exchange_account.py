import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials


@dataclass(frozen=True, slots=True)
class ExchangeAccount:
    """Which account on the exchange some credentials operate: a digest of their public fields, and the fields.

    The API cannot open sealed credentials, yet it must refuse credentials of another exchange account (R0.2.4); the
    digest answers that question (ADR 0019). The public fields are the ones the exchange does not declare secret
    (ADR 0158), kept in clear so a replacement asks only the secret ones and the account shows them (Bug 401, ADR
    campi-pubblici-del-conto-conservati-in-chiaro). None for an account registered before they were kept.
    """

    fingerprint: str
    public_fields: Mapping[str, str] | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if self.public_fields is not None:
            # A copy: what the caller holds can change, the account cannot.
            object.__setattr__(self, "public_fields", dict(self.public_fields))

    @classmethod
    def of(cls, credentials: Credentials, fields: Iterable[CredentialField]) -> ExchangeAccount:
        public = {
            credential_field.name: credentials.value(credential_field.name)
            for credential_field in fields
            if not credential_field.secret
        }
        digest = hashlib.sha256("\n".join(value.lower() for value in public.values()).encode()).hexdigest()
        return cls(digest, public)
