import json
from collections.abc import Mapping

from nacl.exceptions import CryptoError
from nacl.public import SealedBox

from autotrading.adapters.outbound.libsodium.mail_password_sealer import PASSWORD_FIELD
from autotrading.adapters.outbound.libsodium.opener import private_key_of, record_opening
from autotrading.application.notifications.errors import MailPasswordNotOpenedError
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId


class SodiumMailPasswordOpenerAdapter:
    """Opens the password of the mail server of a tenant in the worker, the only service that receives the private
    keys (ADR 0007, ADR server-di-posta-per-tenant).

    Bound to the tenant of the message: the sealed text must name it, so a password copied onto another tenant is
    refused.
    """

    def __init__(self, private_keys: Mapping[int, bytes], tenant_id: TenantId) -> None:
        self._boxes = {version: SealedBox(private_key_of(raw)) for version, raw in private_keys.items()}
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"SodiumMailPasswordOpenerAdapter(tenant_id={self._tenant_id.value}, key_versions={sorted(self._boxes)})"

    def open(self, sealed: SealedMailPassword) -> str:
        try:
            password = self._password_in(sealed)
        except MailPasswordNotOpenedError:
            self._record(sealed, opened=False)
            raise
        self._record(sealed, opened=True)
        return password

    def _record(self, sealed: SealedMailPassword, *, opened: bool) -> None:
        record_opening("posta", "server di posta", self._tenant_id, sealed.key_version, opened=opened)

    def _password_in(self, sealed: SealedMailPassword) -> str:
        document = self._document_of(sealed)
        password = document.get(PASSWORD_FIELD)
        if document.get("tenant_id") != str(self._tenant_id.value) or not isinstance(password, str) or not password:
            raise MailPasswordNotOpenedError
        return password

    def _document_of(self, sealed: SealedMailPassword) -> Mapping[str, object]:
        box = self._boxes.get(sealed.key_version)
        if box is None:
            raise MailPasswordNotOpenedError
        try:
            document = json.loads(box.decrypt(sealed.ciphertext))
        except (CryptoError, ValueError) as error:
            # Every failure to open is the same refusal for the caller: the reason would only help an attacker.
            raise MailPasswordNotOpenedError from error
        if not isinstance(document, Mapping):
            raise MailPasswordNotOpenedError
        return document
