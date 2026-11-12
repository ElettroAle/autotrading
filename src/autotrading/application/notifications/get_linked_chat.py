from autotrading.application.notifications.ports import LinkedChatRepositoryPort
from autotrading.domain.notifications.linked_chat import LinkedChat


class GetLinkedChatUseCase:
    """The chat linked to the tenant, if any (R1.8.1)."""

    def __init__(self, chats: LinkedChatRepositoryPort) -> None:
        self._chats = chats

    def execute(self) -> LinkedChat | None:
        return self._chats.get()
