import json

from nacl.public import SealedBox

from autotrading.adapters.outbound.libsodium.sealer import public_key_of
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId

PASSWORD_FIELD = "mail_password"  # noqa: S105 - the name of the field, never the password


class SodiumMailPasswordSealerAdapter:
    """Seals the password of the mail server of a tenant with the public key of the installation: the API can encrypt
    but never decrypt (ADR server-di-posta-per-tenant).

    The sealed text names the tenant, so the opener refuses a password copied onto another tenant.
    """

    def __init__(self, public_key: bytes, key_version: int, tenant_id: TenantId) -> None:
        self._box = SealedBox(public_key_of(public_key))
        self._key_version = key_version
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"SodiumMailPasswordSealerAdapter(key_version={self._key_version})"

    def seal(self, password: str) -> SealedMailPassword:
        document = {"tenant_id": str(self._tenant_id.value), PASSWORD_FIELD: password}
        plaintext = json.dumps(document, separators=(",", ":")).encode()
        return SealedMailPassword(self._key_version, self._box.encrypt(plaintext))
