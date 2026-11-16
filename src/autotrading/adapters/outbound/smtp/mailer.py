import smtplib
import ssl
from email.message import EmailMessage

from autotrading.application.notifications.errors import EmailNotDeliveredError
from autotrading.domain.notifications.email_address import EmailAddress

# The port of SMTP over TLS from the first byte; on every other port the connection is secured with STARTTLS.
IMPLICIT_TLS_PORT = 465
TIMEOUT_SECONDS = 10.0


class SmtpDisabledMailerAdapter:
    """Stands for the mail service until the installation has one: every email is a recorded failure, and the flows
    go on (R3.5.2).
    """

    def send(self, address: EmailAddress, subject: str, text: str) -> None:  # noqa: ARG002 - the signature of the port
        raise EmailNotDeliveredError


class SmtpMailServiceAdapter:
    """Whether the installation has a mail service, as its configuration declares (R3.5.2)."""

    def __init__(self, configured: bool) -> None:
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured


class SmtpMailerAdapter:
    """Sends the emails of the notifications through the mail service of the installation, one connection per email
    (ADR canale-email-delle-notifiche-con-smtp).
    """

    def __init__(self, host: str, port: int, sender: str, login: tuple[str, str] | None) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._login = login

    def __repr__(self) -> str:
        return f"SmtpMailerAdapter(host={self._host!r}, port={self._port})"

    def send(self, address: EmailAddress, subject: str, text: str) -> None:
        message = _message_of(self._sender, address, subject, text)
        try:
            with self._connect() as server:
                self._secure(server)
                self._authenticate(server)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as error:
            # The permanence stays with the base error: a refusal of the mail service carries no code that decides.
            raise EmailNotDeliveredError from error

    def _connect(self) -> smtplib.SMTP:
        if self._port == IMPLICIT_TLS_PORT:
            return smtplib.SMTP_SSL(
                self._host, self._port, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
            )
        return smtplib.SMTP(self._host, self._port, timeout=TIMEOUT_SECONDS)

    def _secure(self, server: smtplib.SMTP) -> None:
        if self._port != IMPLICIT_TLS_PORT:
            server.starttls(context=ssl.create_default_context())

    def _authenticate(self, server: smtplib.SMTP) -> None:
        if self._login is not None:
            server.login(*self._login)


def _message_of(sender: str, address: EmailAddress, subject: str, text: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = address.value
    message["Subject"] = subject
    message.set_content(text)
    return message
