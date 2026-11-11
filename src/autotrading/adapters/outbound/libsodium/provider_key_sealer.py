import json

from nacl.public import SealedBox

from autotrading.adapters.outbound.libsodium.sealer import public_key_of
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId


class SodiumProviderKeySealerAdapter:
    """Seals provider keys with the public key of the installation: the API can encrypt but never decrypt (ADR 0029).

    The sealed text names tenant and provider, so the opener refuses a key copied onto another tenant or provider.
    """

    def __init__(self, public_key: bytes, key_version: int, tenant_id: TenantId) -> None:
        self._box = SealedBox(public_key_of(public_key))
        self._key_version = key_version
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"SodiumProviderKeySealerAdapter(key_version={self._key_version})"

    def seal(self, provider: ProviderName, key: ProviderKey) -> SealedProviderKey:
        document = {"tenant_id": str(self._tenant_id.value), "provider": provider.value, "key": key.secret}
        plaintext = json.dumps(document, separators=(",", ":")).encode()
        return SealedProviderKey(self._key_version, self._box.encrypt(plaintext))
