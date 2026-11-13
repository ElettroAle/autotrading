import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from nacl.exceptions import CryptoError
from nacl.public import PrivateKey, SealedBox

from autotrading.application.accounts.errors import CredentialsNotOpenedError
from autotrading.application.flows.errors import FlowCredentialsNotOpenedError
from autotrading.application.orders.errors import OrderCredentialsNotOpenedError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId

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
        sealed = account.credentials
        credentials = self._opened(sealed.key_version, sealed.ciphertext, account.tenant_id, account.id.value)
        if credentials is None:
            raise CredentialsNotOpenedError
        return credentials

    def open_access(self, sealed: SealedAccess) -> TradingAccess:
        """The same opening for the orders context, which signs its orders with it (ADR 0023)."""
        credentials = self._opened(sealed.key_version, sealed.ciphertext, sealed.tenant_id, sealed.account_id)
        if credentials is None:
            raise OrderCredentialsNotOpenedError
        return TradingAccess(sealed.exchange, credentials.account_address, credentials.secret_key)

    def open_address(self, sealed: SealedAddress) -> str:
        """The same opening for the flows context, which only reads the account on its exchange (ADR 0044)."""
        credentials = self._opened(sealed.key_version, sealed.ciphertext, sealed.tenant_id, sealed.account_id)
        if credentials is None:
            raise FlowCredentialsNotOpenedError
        return credentials.account_address

    def _opened(self, key_version: int, ciphertext: bytes, tenant_id: TenantId, account_id: UUID) -> Credentials | None:
        document = self._document_of(key_version, ciphertext)
        if document is None or (document.get("tenant_id"), document.get("account_id")) != (
            str(tenant_id.value),
            str(account_id),
        ):
            return None
        return _credentials_of(document)

    def _document_of(self, key_version: int, ciphertext: bytes) -> Mapping[str, Any] | None:
        box = self._boxes.get(key_version)
        if box is None:
            return None
        try:
            document = json.loads(box.decrypt(ciphertext))
        except CryptoError, ValueError:
            # Every failure to open is the same refusal for the caller: the reason would only help an attacker.
            return None
        if not isinstance(document, Mapping):
            return None
        return document


def private_key_of(raw: bytes) -> PrivateKey:
    if len(raw) != PRIVATE_KEY_BYTES:
        raise InvalidPrivateCredentialsKeyError
    return PrivateKey(raw)


def _credentials_of(document: Mapping[str, Any]) -> Credentials | None:
    address, secret = document.get("account_address"), document.get("secret_key")
    if not isinstance(address, str) or not isinstance(secret, str):
        return None
    return Credentials(address, secret)
