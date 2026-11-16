"""The emails of the notifications through the mail service of the installation, against a server in memory that
answers as smtplib does (ADR canale-email-delle-notifiche-con-smtp).
"""

import smtplib
import ssl
from email.message import EmailMessage
from types import TracebackType
from typing import ClassVar

import pytest

from autotrading.adapters.outbound.smtp import mailer
from autotrading.adapters.outbound.smtp.mailer import (
    SmtpDisabledMailerAdapter,
    SmtpMailerAdapter,
    SmtpMailServiceAdapter,
)
from autotrading.application.notifications.errors import EmailNotDeliveredError, MessageNotDeliveredError
from autotrading.domain.notifications.email_address import EmailAddress

ANNA = EmailAddress.parse("anna@example.com")
SENDER = "notifiche@autotrading.example"


class InMemorySmtpServer:
    """A connection to a mail server: what it was told, and the step at which it refuses, if any."""

    opened: ClassVar[list[InMemorySmtpServer]] = []
    refuse_at: ClassVar[str | None] = None

    def __init__(self, host: str, port: int, timeout: float, context: ssl.SSLContext | None = None) -> None:
        self.address = (host, port)
        self.timeout = timeout
        self.implicit_tls = context is not None
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
        self.secured = isinstance(context, ssl.SSLContext)

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


def sent_through(port: int, login: tuple[str, str] | None = None) -> InMemorySmtpServer:
    SmtpMailerAdapter("smtp.example", port, SENDER, login).send(ANNA, "alfa: in pausa", "alfa: in pausa, credito")
    [connection] = InMemorySmtpServer.opened
    return connection


def test_an_email_carries_sender_address_subject_and_text() -> None:
    connection = sent_through(587)

    [message] = connection.messages
    assert (message["From"], message["To"], message["Subject"]) == (SENDER, "anna@example.com", "alfa: in pausa")
    assert message.get_content().strip() == "alfa: in pausa, credito"


def test_on_the_submission_port_the_connection_is_secured_with_starttls_and_then_closed() -> None:
    connection = sent_through(587)

    assert connection.address == ("smtp.example", 587)
    assert (connection.implicit_tls, connection.secured, connection.closed) == (False, True, True)
    assert connection.timeout == mailer.TIMEOUT_SECONDS


def test_on_port_465_the_connection_is_tls_from_the_start() -> None:
    connection = sent_through(465)

    assert (connection.implicit_tls, connection.secured, connection.closed) == (True, False, True)


def test_with_a_user_the_adapter_logs_in_before_sending() -> None:
    connection = sent_through(587, ("notifiche", "PASSWORD-FAKE"))

    assert connection.logins == [("notifiche", "PASSWORD-FAKE")]
    assert len(connection.messages) == 1


def test_without_a_user_the_adapter_sends_without_logging_in() -> None:
    assert sent_through(587).logins == []


@pytest.mark.parametrize("step", ["connect", "starttls", "login", "send"])
def test_a_refusal_of_the_server_is_an_email_not_delivered_that_keeps_its_cause_and_is_retried(step: str) -> None:
    InMemorySmtpServer.refuse_at = step
    adapter = SmtpMailerAdapter("smtp.example", 587, SENDER, ("notifiche", "PASSWORD-FAKE"))

    with pytest.raises(EmailNotDeliveredError) as raised:
        adapter.send(ANNA, "s", "t")

    assert isinstance(raised.value.__cause__, (smtplib.SMTPException, OSError))
    assert not raised.value.permanent
    assert "PASSWORD-FAKE" not in repr(adapter)
    assert all(connection.closed for connection in InMemorySmtpServer.opened)


def test_the_disabled_mailer_fails_every_email_so_the_failure_is_recorded() -> None:
    with pytest.raises(MessageNotDeliveredError):
        SmtpDisabledMailerAdapter().send(ANNA, "s", "t")

    assert InMemorySmtpServer.opened == []


@pytest.mark.parametrize("configured", [True, False])
def test_the_mail_service_tells_whether_the_installation_has_one(configured: bool) -> None:
    assert SmtpMailServiceAdapter(configured).is_configured() is configured
