import hashlib

from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId

KEY_VERSION = 1


class FakeCredentialSealerAdapter:
    """Seals into an opaque digest bound to tenant and account; nothing readable survives, as with the real key."""

    def __init__(self, tenant_id: TenantId) -> None:
        self._tenant_id = tenant_id

    def seal(self, account_id: AccountId, credentials: Credentials) -> SealedCredentials:
        material = f"{self._tenant_id.value}|{account_id.value}|{credentials.account_address}|{credentials.secret_key}"
        return SealedCredentials(KEY_VERSION, hashlib.sha256(material.encode()).digest())
