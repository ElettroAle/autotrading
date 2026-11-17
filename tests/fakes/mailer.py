from dataclasses import dataclass

from autotrading.application.notifications.errors import EmailNotDeliveredError, MailServerRefusedLoginError
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.mail_server import MailServer
from autotrading.domain.notifications.outbox_message import EmailMessage


@dataclass(frozen=True, slots=True)
class SentEmail:
    """An email as its address reads it: the text ends with its links (ADR link-nei-messaggi-telegram-ed-email)."""

    address: EmailAddress
    subject: str
    text: str


@dataclass(frozen=True, slots=True)
class MailLogin:
    """Where an email left from: the server it reached and the password it logged in with."""

    host: str
    port: int
    username: str
    password: str
    sender: str


class FakeMailerAdapter:
    """The mail servers as the tests see them: what each address received and from where, a server that refuses every
    email, or one that refuses the login."""

    def __init__(self) -> None:
        self.accepting = True
        self.refusing_login = False
        self.sent: list[SentEmail] = []
        self.logins: list[MailLogin] = []

    def send(self, server: MailServer, password: str, email: EmailMessage) -> None:
        if self.refusing_login:
            raise MailServerRefusedLoginError
        if not self.accepting:
            raise EmailNotDeliveredError
        self.logins.append(MailLogin(server.host, server.port, server.username, password, server.sender.value))
        self.sent.append(SentEmail(email.address, email.subject, email.body))

    def received_by(self, address: str) -> list[SentEmail]:
        return [email for email in self.sent if email.address.value == address]

    def sent_from(self, address: str) -> list[MailLogin]:
        return [login for login, email in zip(self.logins, self.sent, strict=True) if email.address.value == address]
