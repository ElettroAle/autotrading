from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.domain.notifications.chat_id import ChatId


class FakeMessengerAdapter:
    """Telegram as the tests see it: what each chat received, or a Telegram that does not answer."""

    def __init__(self) -> None:
        self.reachable = True
        self.sent: list[tuple[ChatId, str]] = []

    def send(self, chat_id: ChatId, text: str) -> None:
        if not self.reachable:
            raise MessageNotDeliveredError
        self.sent.append((chat_id, text))

    def received_by(self, chat_id: ChatId) -> list[str]:
        return [text for receiver, text in self.sent if receiver == chat_id]
