from dataclasses import dataclass, field
from uuid import UUID

from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class SealedAddress:
    """What the worker opens to read an account on its exchange: its exchange and its credentials as they are stored,
    sealed with the public key of the installation (ADR 0007). Only the address is taken from them: the readings of
    the exchange are public and sign nothing.
    """

    tenant_id: TenantId
    account_id: UUID
    exchange: str
    key_version: int
    ciphertext: bytes = field(repr=False)
