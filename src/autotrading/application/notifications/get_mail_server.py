from dataclasses import dataclass

from autotrading.application.notifications.ports import MailServerRepositoryPort
from autotrading.domain.notifications.mail_security import MailSecurity


@dataclass(frozen=True, slots=True)
class MailServerSettings:
    """The mail server of the tenant as the user reads it: never its password, only that it is saved (R3.5.5)."""

    host: str
    port: int
    security: MailSecurity
    username: str
    sender: str
    password_saved: bool


class GetMailServerUseCase:
    """The mail server the emails of the tenant leave from, without its password; none until the user saves one."""

    def __init__(self, servers: MailServerRepositoryPort) -> None:
        self._servers = servers

    def execute(self) -> MailServerSettings | None:
        server = self._servers.get()
        if server is None:
            return None
        return MailServerSettings(
            server.host, server.port, server.security, server.username, server.sender.value, password_saved=True
        )
