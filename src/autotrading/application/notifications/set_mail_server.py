from dataclasses import dataclass, field

from autotrading.application.notifications.errors import MailPasswordRequiredError
from autotrading.application.notifications.ports import MailPasswordSealerPort, MailServerRepositoryPort
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.mail_server import MailServer, MailServerAddress
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class SetMailServerCommand:
    host: str
    port: int
    security: MailSecurity
    username: str
    sender: str
    # None, or only spaces, keeps the password saved before (R3.5.5).
    password: str | None = field(repr=False)


class SetMailServerUseCase:
    """Keeps the mail server the emails of the tenant leave from, with its password sealed, replacing the one kept
    before (R3.5.5, ADR server-di-posta-per-tenant).

    A change without a password keeps the saved one; the first server needs one.
    """

    def __init__(self, tenant_id: TenantId, servers: MailServerRepositoryPort, sealer: MailPasswordSealerPort) -> None:
        self._tenant_id = tenant_id
        self._servers = servers
        self._sealer = sealer

    def execute(self, command: SetMailServerCommand) -> None:
        address = MailServerAddress(command.host, command.port, command.security, command.username, command.sender)
        password = self._password_of(command.password)
        self._servers.save(MailServer.of(self._tenant_id, address, password))

    def _password_of(self, written: str | None) -> SealedMailPassword:
        if written is not None and written.strip():
            return self._sealer.seal(written)
        saved = self._servers.get()
        if saved is None:
            raise MailPasswordRequiredError
        return saved.password
