import logging

from autotrading.adapters.outbound.telegram.bot_api import (
    TelegramBotIdentityAdapter,
    TelegramDisabledMessengerAdapter,
    TelegramInboxAdapter,
    TelegramMessengerAdapter,
    telegram_client,
)
from autotrading.adapters.outbound.telegram.configuration import _TelegramSettings
from autotrading.application.notifications.ports import BotInboxPort, BotStartLinkPort, MessengerPort

operations = logging.getLogger("autotrading.notifications")


def telegram_adapters(token: str | None) -> tuple[MessengerPort, BotInboxPort | None, BotStartLinkPort | None]:
    """The bot of the installation: without its token the notifications are off and no bot answers (ADR 0035)."""
    settings = _TelegramSettings(token)
    if settings.token is None:
        operations.warning("bot Telegram non configurato: notifiche disattivate")
        return TelegramDisabledMessengerAdapter(), None, None
    client = telegram_client(settings.token)
    return TelegramMessengerAdapter(client), TelegramInboxAdapter(client), TelegramBotIdentityAdapter(client)
