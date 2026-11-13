"""The Telegram adapters of the installation: without the token of the bot the notifications are off (ADR 0035)."""

import logging

import pytest

from autotrading.adapters.outbound.telegram.bot_api import (
    TelegramBotIdentityAdapter,
    TelegramDisabledMessengerAdapter,
    TelegramInboxAdapter,
    TelegramMessengerAdapter,
)
from autotrading.adapters.outbound.telegram.composition import telegram_adapters
from autotrading.adapters.outbound.telegram.configuration import _TelegramSettings
from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.domain.notifications.chat_id import ChatId


def test_without_a_token_the_messenger_is_the_disabled_one_and_no_bot_answers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        messenger, inbox, start_link = telegram_adapters(None)

    assert isinstance(messenger, TelegramDisabledMessengerAdapter)
    assert (inbox, start_link) == (None, None)
    assert "bot Telegram non configurato" in caplog.text


def test_the_disabled_messenger_fails_every_message_so_the_failure_is_recorded() -> None:
    with pytest.raises(MessageNotDeliveredError):
        TelegramDisabledMessengerAdapter().send(ChatId(1), "text")


def test_with_a_token_messenger_inbox_and_start_link_talk_to_telegram() -> None:
    messenger, inbox, start_link = telegram_adapters("BOT-FAKE")

    assert isinstance(messenger, TelegramMessengerAdapter)
    assert isinstance(inbox, TelegramInboxAdapter)
    assert isinstance(start_link, TelegramBotIdentityAdapter)


def test_the_token_never_appears_in_the_settings_repr() -> None:
    assert "BOT-FAKE" not in repr(_TelegramSettings("BOT-FAKE"))
