from dataclasses import dataclass, field
from uuid import UUID

from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class SealedAccess:
    """What the worker opens to sign the orders of an account: its exchange and its credentials as they are stored,
    sealed with the public key of the installation (ADR 0007).
    """

    tenant_id: TenantId
    account_id: UUID
    exchange: str
    key_version: int
    ciphertext: bytes = field(repr=False)
