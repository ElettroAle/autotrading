from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID

from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.verification.errors import VerificationCredentialsMissingError

MASK = "***"


@dataclass(frozen=True, slots=True)
class SealedVerificationAccess:
    """What the worker opens to read an account for the procedure: its exchange and its credentials as they are
    stored, sealed with the public key of the installation (ADR 0007).
    """

    tenant_id: TenantId
    account_id: UUID
    exchange: str
    key_version: int
    ciphertext: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class VerificationAccess:
    """The opened credentials the procedure reads the account with, proving they still work on the exchange.

    The fields carry the names the exchange declares: only its adapter knows which is which (Bug 284). Never shown in
    answers, logs or errors, so the representation masks them (R0.2.3).
    """

    fields: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        if not self.fields or not all(value.strip() for value in self.fields.values()):
            raise VerificationCredentialsMissingError
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    def value(self, name: str) -> str:
        found = self.fields.get(name)
        if found is None:
            raise VerificationCredentialsMissingError
        return found

    def __hash__(self) -> int:
        return hash(frozenset(self.fields.items()))

    def __repr__(self) -> str:
        return f"VerificationAccess({MASK})"

    __str__ = __repr__
