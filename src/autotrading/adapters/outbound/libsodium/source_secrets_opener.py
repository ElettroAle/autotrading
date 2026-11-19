import json
from collections.abc import Mapping

from nacl.exceptions import CryptoError
from nacl.public import SealedBox

from autotrading.adapters.outbound.libsodium.opener import private_key_of, record_opening
from autotrading.application.sources.errors import SourceSecretsNotOpenedError
from autotrading.domain.sources.source_credentials import SourceCredentials


class SodiumSourceSecretsOpenerAdapter:
    """Opens the secret values of the credentials of the adapters of the sources in the worker, the only service that
    receives the private keys (ADR 0007, R4.1.2, ADR credenziali-degli-adapter-delle-fonti).

    The sealed text must name the tenant and the adapter of the credentials, so secrets copied onto another tenant or
    adapter are refused.
    """

    def __init__(self, private_keys: Mapping[int, bytes]) -> None:
        self._boxes = {version: SealedBox(private_key_of(raw)) for version, raw in private_keys.items()}

    def __repr__(self) -> str:
        return f"SodiumSourceSecretsOpenerAdapter(key_versions={sorted(self._boxes)})"

    def open(self, credentials: SourceCredentials) -> Mapping[str, str]:
        try:
            secrets = self._secrets_of(credentials)
        except SourceSecretsNotOpenedError:
            self._record(credentials, opened=False)
            raise
        self._record(credentials, opened=True)
        return secrets

    def _record(self, credentials: SourceCredentials, *, opened: bool) -> None:
        subject = f"adapter {credentials.adapter}"
        record_opening("fonte", subject, credentials.tenant_id, credentials.sealed.key_version, opened=opened)

    def _secrets_of(self, credentials: SourceCredentials) -> Mapping[str, str]:
        document = self._document_of(credentials)
        expected = (str(credentials.tenant_id.value), credentials.adapter)
        secrets = _secrets_in(document)
        if (document.get("tenant_id"), document.get("adapter")) != expected or secrets is None:
            raise SourceSecretsNotOpenedError(credentials.adapter)
        return secrets

    def _document_of(self, credentials: SourceCredentials) -> Mapping[str, object]:
        box = self._boxes.get(credentials.sealed.key_version)
        if box is None:
            raise SourceSecretsNotOpenedError(credentials.adapter)
        try:
            document = json.loads(box.decrypt(credentials.sealed.ciphertext))
        except (CryptoError, ValueError) as error:
            # Every failure to open is the same refusal for the caller: the reason would only help an attacker.
            raise SourceSecretsNotOpenedError(credentials.adapter) from error
        if not isinstance(document, Mapping):
            raise SourceSecretsNotOpenedError(credentials.adapter)
        return document


def _secrets_in(document: Mapping[str, object]) -> dict[str, str] | None:
    secrets = document.get("secrets")
    if not isinstance(secrets, Mapping) or not all(isinstance(value, str) for value in secrets.values()):
        return None
    return {str(name): str(value) for name, value in secrets.items()}
