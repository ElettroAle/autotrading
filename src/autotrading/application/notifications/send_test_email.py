from autotrading.application.notifications.errors import MailServerNotConfiguredError, NoNotificationEmailToTestError
from autotrading.application.notifications.ports import MailerPort, MailServerAccess, NotificationEmailRepositoryPort
from autotrading.domain.notifications.mail_server import MailServer
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.outbox_message import EmailMessage


class SendTestEmailUseCase:
    """Sends the test email now, from the mail server of the tenant to the address of its notifications, in the worker
    that alone opens the password (R3.5.5, ADR invio-dal-server-di-posta-del-tenant).

    It skips the outbox so that the user sees at once why nothing arrives: no server first, then no address, then the
    refusal of the server.
    """

    def __init__(
        self, emails: NotificationEmailRepositoryPort, mail_servers: MailServerAccess, mailer: MailerPort
    ) -> None:
        self._emails = emails
        self._mail_servers = mail_servers
        self._mailer = mailer

    def execute(self) -> None:
        server = self._server()
        email = self._address_to_test()
        password = self._mail_servers.opener.open(server.password)
        test = Notification.test()
        self._mailer.send(server, password, EmailMessage(email.address, test.title, test.text))

    def _server(self) -> MailServer:
        server = self._mail_servers.servers.get()
        if server is None:
            raise MailServerNotConfiguredError
        return server

    def _address_to_test(self) -> NotificationEmail:
        email = self._emails.get()
        if email is None:
            raise NoNotificationEmailToTestError
        return email
