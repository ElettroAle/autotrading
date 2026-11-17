"""The emails of the notifications through the mail server of their tenant, against a server in memory that answers as
smtplib does (ADR invio-dal-server-di-posta-del-tenant).
"""

import smtplib
import ssl
from email.message import EmailMessage
from types import TracebackType
from typing import ClassVar

import pytest

from autotrading.adapters.outbound.smtp import mailer
from autotrading.adapters.outbound.smtp.mailer import SmtpMailerAdapter
from autotrading.application.notifications.errors import EmailNotDeliveredError, MailServerRefusedLoginError
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.mail_server import MailServer, MailServerAddress
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId

ANNA = EmailAddress.parse("anna@example.com")
SENDER = "notifiche@autotrading.example"
PASSWORD = "PASSWORD-FAKE"  # noqa: S105 - the password of a fake mail server


def a_server(port: int = 587, security: MailSecurity = MailSecurity.STARTTLS) -> MailServer:
    address = MailServerAddress("smtp.example", port, security, "notifiche", SENDER)
    return MailServer.of(TenantId.new(), address, SealedMailPassword(1, b"sealed"))


def verifies(context: ssl.SSLContext) -> bool:
    return context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED


class InMemorySmtpServer:
    """A connection to a mail server: what it was told, and the step at which it refuses, if any."""

    opened: ClassVar[list[InMemorySmtpServer]] = []
    refuse_at: ClassVar[str | None] = None

    def __init__(self, host: str, port: int, timeout: float, context: ssl.SSLContext | None = None) -> None:
        self.address = (host, port)
        self.timeout = timeout
        # Only a context that checks the certificate and the name of the server secures the connection.
        self.implicit_tls = context is not None and verifies(context)
        self.secured = False
        self.logins: list[tuple[str, str]] = []
        self.messages: list[EmailMessage] = []
        self.closed = False
        self._refuse("connect")
        InMemorySmtpServer.opened.append(self)

    def __enter__(self) -> InMemorySmtpServer:
        return self

    def __exit__(
        self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None
    ) -> None:
        self.closed = True

    def starttls(self, context: ssl.SSLContext) -> None:
        self._refuse("starttls")
        self.secured = verifies(context)

    def login(self, user: str, password: str) -> None:
        self._refuse("login")
        self.logins.append((user, password))

    def send_message(self, message: EmailMessage) -> None:
        self._refuse("send")
        self.messages.append(message)

    def _refuse(self, step: str) -> None:
        if step != InMemorySmtpServer.refuse_at:
            return
        if step == "connect":
            raise ConnectionRefusedError(111, "Connection refused")
        if step == "login":
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication failed")
        raise smtplib.SMTPRecipientsRefused({ANNA.value: (550, b"5.1.1 mailbox unavailable")})


@pytest.fixture(autouse=True)
def server(monkeypatch: pytest.MonkeyPatch) -> type[InMemorySmtpServer]:
    InMemorySmtpServer.opened = []
    InMemorySmtpServer.refuse_at = None
    monkeypatch.setattr(smtplib, "SMTP", InMemorySmtpServer)
    monkeypatch.setattr(smtplib, "SMTP_SSL", InMemorySmtpServer)
    return InMemorySmtpServer


def sent_through(server: MailServer) -> InMemorySmtpServer:
    SmtpMailerAdapter().send(server, PASSWORD, ANNA, "alfa: in pausa", "alfa: in pausa, credito")
    [connection] = InMemorySmtpServer.opened
    return connection


def test_an_email_carries_sender_address_subject_and_text() -> None:
    connection = sent_through(a_server())

    [message] = connection.messages
    assert (message["From"], message["To"], message["Subject"]) == (SENDER, "anna@example.com", "alfa: in pausa")
    assert message.get_content().strip() == "alfa: in pausa, credito"


def test_an_email_with_emoji_on_several_lines_keeps_subject_and_text_intact_as_plain_text() -> None:
    """ADR resa-della-notifica-per-telegram-ed-email: text/plain in UTF-8, the subject encoded by EmailMessage."""
    subject = "⏸️ alfa: in pausa"
    status = "Flusso: 312,40 USDC · PnL +12,40 USDC · nessuna posizione aperta · in pausa"
    text = f"{subject}\n\nMotivo: credito esaurito\n{status}"

    SmtpMailerAdapter().send(a_server(), PASSWORD, ANNA, subject, text)

    [connection] = InMemorySmtpServer.opened
    [message] = connection.messages
    assert message["Subject"] == subject
    assert message.get_content_type() == "text/plain"
    assert message.get_content_charset() == "utf-8"
    assert message.get_content() == f"{text}\n"


@pytest.mark.parametrize("port", [587, 25, 465])
def test_with_starttls_the_connection_is_secured_after_connecting_whatever_the_port(port: int) -> None:
    connection = sent_through(a_server(port, MailSecurity.STARTTLS))

    assert connection.address == ("smtp.example", port)
    assert (connection.implicit_tls, connection.secured, connection.closed) == (False, True, True)
    assert connection.timeout == mailer.TIMEOUT_SECONDS


@pytest.mark.parametrize("port", [465, 2465])
def test_with_tls_the_connection_is_tls_from_the_start_whatever_the_port(port: int) -> None:
    connection = sent_through(a_server(port, MailSecurity.TLS))

    assert connection.address == ("smtp.example", port)
    assert (connection.implicit_tls, connection.secured, connection.closed) == (True, False, True)


def test_the_adapter_logs_in_with_the_user_of_the_server_and_its_password_before_sending() -> None:
    connection = sent_through(a_server())

    assert connection.logins == [("notifiche", PASSWORD)]
    assert len(connection.messages) == 1


def test_a_login_refused_by_the_server_tells_the_user_to_check_user_and_password() -> None:
    InMemorySmtpServer.refuse_at = "login"

    with pytest.raises(MailServerRefusedLoginError) as raised:
        SmtpMailerAdapter().send(a_server(), PASSWORD, ANNA, "s", "t")

    assert str(raised.value) == "il server di posta ha rifiutato l'accesso: controlla utente e password"
    assert isinstance(raised.value.__cause__, smtplib.SMTPAuthenticationError)
    assert raised.value.status_code == 400
    assert not raised.value.permanent


@pytest.mark.parametrize("step", ["connect", "starttls", "send"])
def test_a_refusal_of_the_server_is_an_email_not_delivered_that_keeps_its_cause_and_is_retried(step: str) -> None:
    InMemorySmtpServer.refuse_at = step
    adapter = SmtpMailerAdapter()

    with pytest.raises(EmailNotDeliveredError) as raised:
        adapter.send(a_server(), PASSWORD, ANNA, "s", "t")

    assert type(raised.value) is EmailNotDeliveredError
    assert isinstance(raised.value.__cause__, (smtplib.SMTPException, OSError))
    assert not raised.value.permanent
    assert PASSWORD not in str(raised.value)
    assert all(connection.closed for connection in InMemorySmtpServer.opened)


def test_the_adapter_holds_no_server_of_its_own() -> None:
    assert repr(SmtpMailerAdapter()) == "SmtpMailerAdapter()"
