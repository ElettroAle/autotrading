from autotrading.application.notifications.ports import MailServerRepositoryPort


class RemoveMailServerUseCase:
    """Removes the mail server of the tenant and its password: no email leaves until the user saves one (R3.5.5)."""

    def __init__(self, servers: MailServerRepositoryPort) -> None:
        self._servers = servers

    def execute(self) -> None:
        self._servers.remove()
