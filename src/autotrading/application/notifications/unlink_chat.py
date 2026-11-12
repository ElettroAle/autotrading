from autotrading.application.notifications.ports import LinkedChatRepositoryPort


class UnlinkChatUseCase:
    """Unlinks the chat of the tenant: its notifications stop, its flows go on (R1.8.1)."""

    def __init__(self, chats: LinkedChatRepositoryPort) -> None:
        self._chats = chats

    def execute(self) -> None:
        self._chats.unlink()
