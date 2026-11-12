from collections.abc import Sequence

from autotrading.application.notifications.errors import BotUnreachableError
from autotrading.application.notifications.ports import BotMessage


class FakeBotInboxAdapter:
    """The messages waiting for the bot: each receive takes them all, like a long poll that confirms them."""

    def __init__(self) -> None:
        self.reachable = True
        self.waiting: list[BotMessage] = []

    def receive(self) -> Sequence[BotMessage]:
        if not self.reachable:
            raise BotUnreachableError
        received, self.waiting = self.waiting, []
        return received
