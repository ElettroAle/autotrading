import smtplib
import ssl
from email.message import EmailMessage

from autotrading.application.notifications.errors import EmailNotDeliveredError, MailServerRefusedLoginError
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.mail_server import MailServer

TIMEOUT_SECONDS = 10.0


class SmtpMailerAdapter:
    """Sends the emails of the notifications through the mail server of their tenant, one connection per email, logged
    in with its user and the password the worker opened (ADR invio-dal-server-di-posta-del-tenant).
    """

    def __repr__(self) -> str:
        return "SmtpMailerAdapter()"

    def send(self, server: MailServer, password: str, address: EmailAddress, subject: str, text: str) -> None:
        message = _message_of(server.sender, address, subject, text)
        try:
            with _connect(server) as connection:
                _secure(server, connection)
                connection.login(server.username, password)
                connection.send_message(message)
        except smtplib.SMTPAuthenticationError as error:
            raise MailServerRefusedLoginError from error
        except (smtplib.SMTPException, OSError) as error:
            # The permanence stays with the base error: a refusal of the mail server carries no code that decides.
            raise EmailNotDeliveredError from error


def _connect(server: MailServer) -> smtplib.SMTP:
    if server.security is MailSecurity.TLS:
        return smtplib.SMTP_SSL(server.host, server.port, timeout=TIMEOUT_SECONDS, context=_verified_context())
    return smtplib.SMTP(server.host, server.port, timeout=TIMEOUT_SECONDS)


def _secure(server: MailServer, connection: smtplib.SMTP) -> None:
    if server.security is MailSecurity.STARTTLS:
        connection.starttls(context=_verified_context())


def _verified_context() -> ssl.SSLContext:
    """A TLS context that checks the certificate and the name of the mail server: never a connection to an impostor."""
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def _message_of(sender: EmailAddress, address: EmailAddress, subject: str, text: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender.value
    message["To"] = address.value
    message["Subject"] = subject
    message.set_content(text)
    return message
