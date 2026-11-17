from dataclasses import dataclass, replace

from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.errors import (
    InvalidMailSenderError,
    InvalidMailServerHostError,
    InvalidMailServerPortError,
    InvalidMailServerUsernameError,
)
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

HIGHEST_PORT = 65535


@dataclass(frozen=True, slots=True)
class MailServerAddress:
    """What the user writes of a mail server, as written: the server makes it a valid one or refuses it."""

    host: str
    port: int
    security: MailSecurity
    username: str
    sender: str


@dataclass(frozen=True, slots=True)
class MailServer(TenantOwned):
    """The mail server the emails of a tenant leave from, one per tenant, with its password sealed (R3.5.5, ADR
    server-di-posta-per-tenant).
    """

    tenant_id: TenantId
    host: str
    port: int
    security: MailSecurity
    username: str
    sender: EmailAddress
    password: SealedMailPassword

    def __post_init__(self) -> None:
        if not self.host or any(character.isspace() for character in self.host):
            raise InvalidMailServerHostError(self.host)
        if not 0 < self.port <= HIGHEST_PORT:
            raise InvalidMailServerPortError(self.port)
        if not self.username:
            raise InvalidMailServerUsernameError(self.username)

    @classmethod
    def of(cls, tenant_id: TenantId, address: MailServerAddress, password: SealedMailPassword) -> MailServer:
        """The server as the user wrote it, without the spaces around; without a sender it sends as its user."""
        host, username = address.host.strip(), address.username.strip()
        if not username:
            raise InvalidMailServerUsernameError(username)
        sender = address.sender.strip() or username
        if not EmailAddress.accepts(sender):
            raise InvalidMailSenderError(sender)
        return cls(tenant_id, host, address.port, address.security, username, EmailAddress(sender), password)

    def with_password(self, password: SealedMailPassword) -> MailServer:
        return replace(self, password=password)
