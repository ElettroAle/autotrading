from autotrading.application.notifications.errors import NoLinkedChatToTestError
from autotrading.application.notifications.ports import LinkedChatRepositoryPort, NotifierPort
from autotrading.domain.notifications.notification import Notification


class SendLinkedChatTestNotificationUseCase:
    """Sends the test notification of R1.8.1 to the chat linked to the tenant, asked from the dashboard (R2.3.6).

    It goes by the road of the real notifications, with the same text as the test asked from the chat.
    """

    def __init__(self, chats: LinkedChatRepositoryPort, notifier: NotifierPort) -> None:
        self._chats = chats
        self._notifier = notifier

    def execute(self) -> None:
        # A notification without a chat is dropped in silence (R1.8.2): the user asking for a test must know instead.
        if self._chats.get() is None:
            raise NoLinkedChatToTestError
        self._notifier.execute(Notification.test())
