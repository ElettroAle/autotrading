import json
from collections.abc import Mapping

from nacl.exceptions import CryptoError
from nacl.public import PrivateKey, SealedBox

from autotrading.application.accounts.errors import CredentialsNotOpenedError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.errors import AutotradingError

PRIVATE_KEY_BYTES = 32


class InvalidPrivateCredentialsKeyError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("chiave privata delle credenziali non valida")


class SodiumCredentialOpenerAdapter:
    """Opens sealed credentials in the worker, the only service that receives the private keys (ADR 0007).

    The key is chosen by the version saved with the sealed text; the sealed text must name the tenant and the
    account asked for, so credentials copied onto another account are refused.
    """

    def __init__(self, private_keys: Mapping[int, bytes]) -> None:
        self._boxes = {version: SealedBox(private_key_of(raw)) for version, raw in private_keys.items()}

    def __repr__(self) -> str:
        return f"SodiumCredentialOpenerAdapter(key_versions={sorted(self._boxes)})"

    def open(self, account: Account) -> Credentials:
        document = self._document_of(account)
        if (document.get("tenant_id"), document.get("account_id")) != (
            str(account.tenant_id.value),
            str(account.id.value),
        ):
            raise CredentialsNotOpenedError
        return _credentials_of(document)

    def _document_of(self, account: Account) -> Mapping[str, object]:
        box = self._boxes.get(account.credentials.key_version)
        if box is None:
            raise CredentialsNotOpenedError
        try:
            document = json.loads(box.decrypt(account.credentials.ciphertext))
        except (CryptoError, ValueError) as error:
            raise CredentialsNotOpenedError from error
        if not isinstance(document, Mapping):
            raise CredentialsNotOpenedError
        return document


def private_key_of(raw: bytes) -> PrivateKey:
    if len(raw) != PRIVATE_KEY_BYTES:
        raise InvalidPrivateCredentialsKeyError
    return PrivateKey(raw)


def _credentials_of(document: Mapping[str, object]) -> Credentials:
    address, secret = document.get("account_address"), document.get("secret_key")
    if not isinstance(address, str) or not isinstance(secret, str):
        raise CredentialsNotOpenedError
    return Credentials(address, secret)
