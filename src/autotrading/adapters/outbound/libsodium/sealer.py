import json

from nacl.exceptions import CryptoError
from nacl.public import PublicKey, SealedBox

from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.errors import AutotradingError
from autotrading.domain.tenancy.tenant_id import TenantId

PUBLIC_KEY_BYTES = 32


class InvalidCredentialsKeyError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("chiave pubblica delle credenziali non valida")


class SodiumCredentialSealerAdapter:
    """Seals credentials with the public key of the installation: the API can encrypt but never decrypt (ADR 0007).

    The sealed text names tenant and account, so the opener refuses credentials copied onto another account.
    """

    def __init__(self, public_key: bytes, key_version: int, tenant_id: TenantId) -> None:
        self._box = SealedBox(public_key_of(public_key))
        self._key_version = key_version
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"SodiumCredentialSealerAdapter(key_version={self._key_version})"

    def seal(self, account_id: AccountId, credentials: Credentials) -> SealedCredentials:
        plaintext = _plaintext(self._tenant_id, account_id, credentials)
        return SealedCredentials(self._key_version, self._box.encrypt(plaintext))


def public_key_of(raw: bytes) -> PublicKey:
    if len(raw) != PUBLIC_KEY_BYTES:
        raise InvalidCredentialsKeyError
    try:
        return PublicKey(raw)
    except CryptoError as error:
        raise InvalidCredentialsKeyError from error


def _plaintext(tenant_id: TenantId, account_id: AccountId, credentials: Credentials) -> bytes:
    document = {
        "tenant_id": str(tenant_id.value),
        "account_id": str(account_id.value),
        "account_address": credentials.account_address,
        "secret_key": credentials.secret_key,
    }
    return json.dumps(document, separators=(",", ":")).encode()
