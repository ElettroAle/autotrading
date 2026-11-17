"""The mail server of a tenant: saved with its password sealed, read without it, removed, and the test email sent from
it at once (R3.5.5, ADR server-di-posta-per-tenant, ADR invio-dal-server-di-posta-del-tenant).
"""

import pytest

from autotrading.application.notifications.errors import (
    EmailNotDeliveredError,
    MailPasswordNotOpenedError,
    MailPasswordRequiredError,
    MailServerNotConfiguredError,
    MailServerRefusedLoginError,
    NoNotificationEmailToTestError,
)
from autotrading.application.notifications.get_mail_server import GetMailServerUseCase, MailServerSettings
from autotrading.application.notifications.remove_mail_server import RemoveMailServerUseCase
from autotrading.application.notifications.request_test_email import RequestTestEmailUseCase
from autotrading.application.notifications.send_test_email import SendTestEmailUseCase
from autotrading.application.notifications.set_mail_server import SetMailServerCommand, SetMailServerUseCase
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.errors import InvalidMailServerPortError
from autotrading.domain.notifications.mail_security import MailSecurity
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.email_test import FakeEmailTestAdapter
from tests.fakes.mailer import FakeMailerAdapter, MailLogin, SentEmail
from tests.fakes.notification_email_repository import (
    InMemoryNotificationEmailRepositoryAdapter,
    NotificationEmailStore,
)
from tests.support.mail_servers import MailServers

ANNA, BRUNO = TenantId.new(), TenantId.new()
ANNA_ADDRESS = EmailAddress.parse("anna@example.com")
PASSWORD = "segreta"  # noqa: S105 - the password of a fake mail server
NEW_PASSWORD = "nuova"  # noqa: S105 - the password of a fake mail server


def a_command(
    *, port: int = 587, security: MailSecurity = MailSecurity.STARTTLS, password: str | None = PASSWORD
) -> SetMailServerCommand:
    return SetMailServerCommand("smtp.example.com", port, security, "anna@example.com", "", password)


class Mail:
    def __init__(self) -> None:
        self.servers = MailServers()
        self.emails: NotificationEmailStore = {}
        self.mailer = FakeMailerAdapter()

    def emails_of(self, tenant_id: TenantId) -> InMemoryNotificationEmailRepositoryAdapter:
        return InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id)

    def save(self, tenant_id: TenantId, command: SetMailServerCommand) -> None:
        servers = self.servers
        SetMailServerUseCase(tenant_id, servers.repository(tenant_id), servers.sealer(tenant_id)).execute(command)

    def read(self, tenant_id: TenantId) -> MailServerSettings | None:
        return GetMailServerUseCase(self.servers.repository(tenant_id)).execute()

    def test_email(self, tenant_id: TenantId) -> SendTestEmailUseCase:
        return SendTestEmailUseCase(self.emails_of(tenant_id), self.servers.access_of(tenant_id), self.mailer)

    def indicate(self, tenant_id: TenantId) -> None:
        self.emails[tenant_id] = NotificationEmail(tenant_id, ANNA_ADDRESS)


@pytest.fixture
def mail() -> Mail:
    return Mail()


def test_a_saved_server_is_read_back_without_its_password(mail: Mail) -> None:
    mail.save(ANNA, a_command())

    assert mail.read(ANNA) == MailServerSettings(
        "smtp.example.com", 587, MailSecurity.STARTTLS, "anna@example.com", "anna@example.com", password_saved=True
    )
    assert PASSWORD not in repr(mail.read(ANNA))


def test_the_saved_password_is_sealed_for_the_tenant(mail: Mail) -> None:
    mail.save(ANNA, a_command())

    sealed = mail.servers.store[ANNA].password
    assert PASSWORD.encode() not in sealed.ciphertext
    assert mail.servers.opener(ANNA).open(sealed) == PASSWORD
    with pytest.raises(MailPasswordNotOpenedError):
        mail.servers.opener(BRUNO).open(sealed)


def test_without_a_server_nothing_is_read(mail: Mail) -> None:
    assert mail.read(ANNA) is None


def test_a_first_server_without_a_password_is_refused(mail: Mail) -> None:
    with pytest.raises(MailPasswordRequiredError, match=r"^password del server di posta mancante$") as raised:
        mail.save(ANNA, a_command(password=None))

    assert raised.value.status_code == 400
    assert mail.read(ANNA) is None


@pytest.mark.parametrize("password", [None, "", "   "])
def test_a_change_without_a_password_keeps_the_saved_one(mail: Mail, password: str | None) -> None:
    mail.save(ANNA, a_command())

    mail.save(ANNA, a_command(port=465, security=MailSecurity.TLS, password=password))

    server = mail.servers.store[ANNA]
    assert (server.port, server.security) == (465, MailSecurity.TLS)
    assert mail.servers.opener(ANNA).open(server.password) == PASSWORD


def test_a_change_with_a_password_replaces_the_saved_one(mail: Mail) -> None:
    mail.save(ANNA, a_command())

    mail.save(ANNA, a_command(password=NEW_PASSWORD))

    assert mail.servers.opener(ANNA).open(mail.servers.store[ANNA].password) == NEW_PASSWORD


def test_a_server_refused_by_its_form_keeps_the_saved_one(mail: Mail) -> None:
    mail.save(ANNA, a_command())

    with pytest.raises(InvalidMailServerPortError):
        mail.save(ANNA, a_command(port=0))

    assert mail.servers.store[ANNA].port == 587


def test_a_removed_server_is_no_more_and_removing_again_is_no_error(mail: Mail) -> None:
    mail.save(ANNA, a_command())
    remove = RemoveMailServerUseCase(mail.servers.repository(ANNA))

    remove.execute()
    remove.execute()

    assert mail.read(ANNA) is None


def test_the_servers_are_isolated_by_tenant(mail: Mail) -> None:
    mail.save(ANNA, a_command())

    assert mail.read(BRUNO) is None


def test_the_test_email_leaves_at_once_from_the_server_of_the_tenant(mail: Mail) -> None:
    mail.save(ANNA, a_command())
    mail.indicate(ANNA)

    mail.test_email(ANNA).execute()

    test = Notification.test()
    assert mail.mailer.sent == [SentEmail(ANNA_ADDRESS, test.title, test.text)]
    assert mail.mailer.logins == [MailLogin("smtp.example.com", 587, "anna@example.com", PASSWORD, "anna@example.com")]


def test_a_test_without_a_server_is_a_conflict_even_before_an_address(mail: Mail) -> None:
    with pytest.raises(MailServerNotConfiguredError, match=r"^server di posta non configurato$") as raised:
        mail.test_email(ANNA).execute()

    assert raised.value.status_code == 409
    assert mail.mailer.sent == []


def test_a_test_without_an_address_is_a_conflict(mail: Mail) -> None:
    mail.save(ANNA, a_command())

    with pytest.raises(NoNotificationEmailToTestError):
        mail.test_email(ANNA).execute()

    assert mail.mailer.sent == []


def test_a_login_refused_by_the_server_is_told_to_the_user(mail: Mail) -> None:
    mail.save(ANNA, a_command())
    mail.indicate(ANNA)
    mail.mailer.refusing_login = True

    with pytest.raises(
        MailServerRefusedLoginError, match=r"^il server di posta ha rifiutato l'accesso: controlla utente e password$"
    ) as raised:
        mail.test_email(ANNA).execute()

    assert raised.value.status_code == 400


def test_an_email_the_server_does_not_take_is_told_to_the_user(mail: Mail) -> None:
    mail.save(ANNA, a_command())
    mail.indicate(ANNA)
    mail.mailer.accepting = False

    with pytest.raises(EmailNotDeliveredError) as raised:
        mail.test_email(ANNA).execute()

    assert raised.value.status_code == 503


def test_a_password_that_cannot_be_opened_is_told_to_the_user(mail: Mail) -> None:
    mail.save(ANNA, a_command())
    mail.indicate(ANNA)
    mail.servers.vault.clear()

    with pytest.raises(MailPasswordNotOpenedError, match=r"^password del server di posta non leggibile"):
        mail.test_email(ANNA).execute()

    assert mail.mailer.sent == []


class Request:
    """The API asking the worker for the test email of a tenant."""

    def __init__(self, mail: Mail, tenant_id: TenantId) -> None:
        self.worker = FakeEmailTestAdapter(mail.test_email(tenant_id).execute)
        self.use_case = RequestTestEmailUseCase(
            mail.emails_of(tenant_id), mail.servers.repository(tenant_id), self.worker
        )


def test_the_api_asks_the_worker_for_the_test_email(mail: Mail) -> None:
    mail.save(ANNA, a_command())
    mail.indicate(ANNA)
    request = Request(mail, ANNA)

    request.use_case.execute()

    assert request.worker.asked == 1
    assert mail.mailer.received_by(ANNA_ADDRESS.value)


def test_the_api_refuses_a_test_without_a_server_before_asking_the_worker(mail: Mail) -> None:
    mail.indicate(ANNA)
    request = Request(mail, ANNA)

    with pytest.raises(MailServerNotConfiguredError):
        request.use_case.execute()

    assert request.worker.asked == 0


def test_the_api_refuses_a_test_without_an_address_before_asking_the_worker(mail: Mail) -> None:
    mail.save(ANNA, a_command())
    request = Request(mail, ANNA)

    with pytest.raises(NoNotificationEmailToTestError):
        request.use_case.execute()

    assert request.worker.asked == 0


def test_the_api_gives_back_the_refusal_of_the_server(mail: Mail) -> None:
    mail.save(ANNA, a_command())
    mail.indicate(ANNA)
    mail.mailer.refusing_login = True

    with pytest.raises(MailServerRefusedLoginError):
        Request(mail, ANNA).use_case.execute()
