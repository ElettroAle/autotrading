import hashlib

from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId

KEY_VERSION = 1

# What the private key would recover from each sealed text: only the worker would read it.
type MailPasswordVault = dict[bytes, tuple[TenantId, str]]


class FakeMailPasswordSealerAdapter:
    """Seals into an opaque digest bound to the tenant; nothing readable survives, as with the real key."""

    def __init__(self, tenant_id: TenantId, vault: MailPasswordVault) -> None:
        self._tenant_id = tenant_id
        self._vault = vault

    def seal(self, password: str) -> SealedMailPassword:
        ciphertext = hashlib.sha256(f"{self._tenant_id.value}|{password}".encode()).digest()
        self._vault[ciphertext] = (self._tenant_id, password)
        return SealedMailPassword(KEY_VERSION, ciphertext)
