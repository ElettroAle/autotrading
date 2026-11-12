from autotrading.application.notifications.link_chat import LinkChatCommand, LinkChatUseCase
from autotrading.application.notifications.ports import BotInboxPort


class AnswerBotMessagesUseCase:
    """One round of the bot: every message received is a link attempt, answered in its chat (R1.8.1)."""

    def __init__(self, inbox: BotInboxPort, link_chat: LinkChatUseCase) -> None:
        self._inbox = inbox
        self._link_chat = link_chat

    def execute(self) -> None:
        for message in self._inbox.receive():
            self._link_chat.execute(LinkChatCommand(message.chat_id, message.text))
