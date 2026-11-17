from collections.abc import Sequence

from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.notification_link import NotificationLink


class FakeMessengerAdapter:
    """Telegram as the tests see it: what each chat received, with the buttons under each message, or a Telegram that
    does not answer."""

    def __init__(self) -> None:
        self.reachable = True
        self.sent: list[tuple[ChatId, str]] = []
        self.buttons: list[tuple[NotificationLink, ...]] = []

    def send(self, chat_id: ChatId, text: str, links: Sequence[NotificationLink] = ()) -> None:
        if not self.reachable:
            raise MessageNotDeliveredError
        self.sent.append((chat_id, text))
        self.buttons.append(tuple(links))

    def received_by(self, chat_id: ChatId) -> list[str]:
        return [text for receiver, text in self.sent if receiver == chat_id]

    def links_received_by(self, chat_id: ChatId) -> list[tuple[NotificationLink, ...]]:
        return [links for (receiver, _), links in zip(self.sent, self.buttons, strict=True) if receiver == chat_id]
