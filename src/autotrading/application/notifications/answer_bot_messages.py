from autotrading.application.notifications.link_chat import LinkChatCommand, LinkChatUseCase
from autotrading.application.notifications.ports import BotInboxPort, BotMessage
from autotrading.application.notifications.send_test_notification import (
    SendTestNotificationCommand,
    SendTestNotificationUseCase,
)
from autotrading.domain.notifications.bot_command import asks_for_test


class AnswerBotMessagesUseCase:
    """One round of the bot: the test command asks for a test notification, every other message is a link
    attempt, each answered in its chat (R1.8.1).
    """

    def __init__(
        self,
        inbox: BotInboxPort,
        link_chat: LinkChatUseCase,
        test_notification: SendTestNotificationUseCase,
    ) -> None:
        self._inbox = inbox
        self._link_chat = link_chat
        self._test_notification = test_notification

    def execute(self) -> None:
        for message in self._inbox.receive():
            self._answer(message)

    def _answer(self, message: BotMessage) -> None:
        if asks_for_test(message.text):
            self._test_notification.execute(SendTestNotificationCommand(message.chat_id))
            return
        self._link_chat.execute(LinkChatCommand(message.chat_id, message.text))
