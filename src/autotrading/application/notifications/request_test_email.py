from autotrading.application.notifications.errors import MailServerNotConfiguredError, NoNotificationEmailToTestError
from autotrading.application.notifications.ports import (
    EmailTestPort,
    MailServerRepositoryPort,
    NotificationEmailRepositoryPort,
)


class RequestTestEmailUseCase:
    """The test email the user asks for from the dashboard, sent now by the worker from the mail server of the tenant
    (R3.5.5, ADR invio-dal-server-di-posta-del-tenant).

    What is missing is refused before the worker is asked; the refusal of the server comes back as it is.
    """

    def __init__(
        self, emails: NotificationEmailRepositoryPort, servers: MailServerRepositoryPort, tests: EmailTestPort
    ) -> None:
        self._emails = emails
        self._servers = servers
        self._tests = tests

    def execute(self) -> None:
        if self._servers.get() is None:
            raise MailServerNotConfiguredError
        if self._emails.get() is None:
            raise NoNotificationEmailToTestError
        self._tests.send_test()
