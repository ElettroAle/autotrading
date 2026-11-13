import json
from collections.abc import Mapping

from nacl.exceptions import CryptoError
from nacl.public import SealedBox

from autotrading.adapters.outbound.libsodium.opener import private_key_of
from autotrading.application.agent.errors import ProviderKeyNotOpenedError
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey


class SodiumProviderKeyOpenerAdapter:
    """Opens provider keys in the worker, the only service that receives the private keys (ADR 0007, ADR 0029).

    The sealed text must name the tenant and the provider of the key, so a key copied onto another tenant or
    provider is refused.
    """

    def __init__(self, private_keys: Mapping[int, bytes]) -> None:
        self._boxes = {version: SealedBox(private_key_of(raw)) for version, raw in private_keys.items()}

    def __repr__(self) -> str:
        return f"SodiumProviderKeyOpenerAdapter(key_versions={sorted(self._boxes)})"

    def open(self, key: RegisteredProviderKey) -> ProviderKey:
        document = self._document_of(key)
        expected = (str(key.tenant_id.value), key.provider.value)
        secret = document.get("key")
        if (document.get("tenant_id"), document.get("provider")) != expected or not isinstance(secret, str):
            raise ProviderKeyNotOpenedError(key.provider)
        return ProviderKey(secret)

    def _document_of(self, key: RegisteredProviderKey) -> Mapping[str, object]:
        box = self._boxes.get(key.sealed.key_version)
        if box is None:
            raise ProviderKeyNotOpenedError(key.provider)
        try:
            document = json.loads(box.decrypt(key.sealed.ciphertext))
        except (CryptoError, ValueError) as error:
            raise ProviderKeyNotOpenedError(key.provider) from error
        if not isinstance(document, Mapping):
            raise ProviderKeyNotOpenedError(key.provider)
        return document
