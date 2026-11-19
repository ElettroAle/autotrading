import json
from collections.abc import Mapping

from nacl.public import SealedBox

from autotrading.adapters.outbound.libsodium.sealer import public_key_of
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.tenancy.tenant_id import TenantId


class SodiumSourceSecretsSealerAdapter:
    """Seals the secret values of the credentials of an adapter of a source with the public key of the installation:
    the API can encrypt but never decrypt (R4.1.2, ADR credenziali-degli-adapter-delle-fonti).

    The sealed text names tenant and adapter, so the opener refuses secrets copied onto another tenant or adapter.
    """

    def __init__(self, public_key: bytes, key_version: int, tenant_id: TenantId) -> None:
        self._box = SealedBox(public_key_of(public_key))
        self._key_version = key_version
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"SodiumSourceSecretsSealerAdapter(key_version={self._key_version})"

    def seal(self, adapter: str, secrets: Mapping[str, str]) -> SealedSourceSecrets:
        document = {"tenant_id": str(self._tenant_id.value), "adapter": adapter, "secrets": dict(secrets)}
        plaintext = json.dumps(document, separators=(",", ":")).encode()
        return SealedSourceSecrets(self._key_version, self._box.encrypt(plaintext))
