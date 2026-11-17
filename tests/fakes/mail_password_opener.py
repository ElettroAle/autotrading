from autotrading.application.notifications.errors import MailPasswordNotOpenedError
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.mail_password_sealer import MailPasswordVault


class FakeMailPasswordOpenerAdapter:
    """Recovers from the vault what the private key would: only a password sealed for its own tenant."""

    def __init__(self, tenant_id: TenantId, vault: MailPasswordVault) -> None:
        self._tenant_id = tenant_id
        self._vault = vault

    def open(self, sealed: SealedMailPassword) -> str:
        tenant_id, password = self._vault.get(sealed.ciphertext, (None, None))
        if tenant_id != self._tenant_id or password is None:
            raise MailPasswordNotOpenedError
        return password
