import hashlib

from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId

KEY_VERSION = 1

# What the private key would recover from each sealed text: only the fake opener reads it.
type SealedVault = dict[bytes, tuple[TenantId, AccountId, Credentials]]


class FakeCredentialSealerAdapter:
    """Seals into an opaque digest bound to tenant and account; nothing readable survives, as with the real key."""

    def __init__(self, tenant_id: TenantId, vault: SealedVault | None = None) -> None:
        self._tenant_id = tenant_id
        self._vault: SealedVault = {} if vault is None else vault

    def seal(self, account_id: AccountId, credentials: Credentials) -> SealedCredentials:
        material = f"{self._tenant_id.value}|{account_id.value}|{credentials.account_address}|{credentials.secret_key}"
        ciphertext = hashlib.sha256(material.encode()).digest()
        self._vault[ciphertext] = (self._tenant_id, account_id, credentials)
        return SealedCredentials(KEY_VERSION, ciphertext)
