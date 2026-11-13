from dataclasses import dataclass, field
from uuid import UUID

from autotrading.domain.tenancy.tenant_id import TenantId

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

    Never shown in answers, logs or errors, so the representation masks address and secret (R0.2.3).
    """

    account_address: str = field(repr=False)
    secret_key: str = field(repr=False)

    def __repr__(self) -> str:
        return f"VerificationAccess({MASK})"

    __str__ = __repr__
