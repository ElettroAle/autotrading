import logging

from autotrading.adapters.outbound.httpx.telegram import (
    HttpxTelegramBotIdentityAdapter,
    HttpxTelegramInboxAdapter,
    HttpxTelegramMessengerAdapter,
    telegram_client,
)
from autotrading.application.notifications.ports import BotIdentityPort, BotInboxPort, MessengerPort

operations = logging.getLogger("autotrading.notifications")


def telegram_channel(
    token: str | None, unconfigured: MessengerPort
) -> tuple[MessengerPort, BotInboxPort | None, BotIdentityPort | None]:
    """The bot of the installation: without its token the notifications are off and no bot answers (ADR 0035)."""
    if token is None:
        operations.warning("bot Telegram non configurato: notifiche disattivate")
        return unconfigured, None, None
    client = telegram_client(token)
    return (
        HttpxTelegramMessengerAdapter(client),
        HttpxTelegramInboxAdapter(client),
        HttpxTelegramBotIdentityAdapter(client),
    )
