"""The bot channel of the installation: without the token of the bot the notifications are off (ADR 0035)."""

import logging

import pytest

from autotrading.adapters.outbound.httpx.telegram import (
    HttpxTelegramBotIdentityAdapter,
    HttpxTelegramInboxAdapter,
    HttpxTelegramMessengerAdapter,
)
from autotrading.adapters.outbound.httpx.telegram_channel import telegram_channel
from autotrading.domain.notifications.chat_id import ChatId


class SilentMessenger:
    def __init__(self) -> None:
        self.sent: list[tuple[ChatId, str]] = []

    def send(self, chat_id: ChatId, text: str) -> None:
        self.sent.append((chat_id, text))


def test_without_a_token_the_messenger_is_the_unconfigured_one_and_no_bot_answers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    unconfigured = SilentMessenger()

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        messenger, inbox, identity = telegram_channel(None, unconfigured)

    assert (messenger, inbox, identity) == (unconfigured, None, None)
    assert "bot Telegram non configurato" in caplog.text


def test_with_a_token_messenger_inbox_and_identity_talk_to_telegram() -> None:
    messenger, inbox, identity = telegram_channel("BOT-FAKE", SilentMessenger())

    assert isinstance(messenger, HttpxTelegramMessengerAdapter)
    assert isinstance(inbox, HttpxTelegramInboxAdapter)
    assert isinstance(identity, HttpxTelegramBotIdentityAdapter)
