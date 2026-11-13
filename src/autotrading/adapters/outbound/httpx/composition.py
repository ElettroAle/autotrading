import httpx

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.httpx.account_state import TIMEOUT_SECONDS
from autotrading.adapters.outbound.httpx.configuration import _telegram_settings_of, _worker_settings_of
from autotrading.adapters.outbound.httpx.telegram_channel import telegram_channel
from autotrading.application.notifications.ports import BotIdentityPort, BotInboxPort, MessengerPort


def httpx_worker_adapters(source: ConfigurationSource) -> tuple[httpx.Client, str]:
    """The client that reaches the worker and the token it presents."""
    settings = _worker_settings_of(source)
    return httpx.Client(base_url=settings.url, timeout=TIMEOUT_SECONDS), settings.token


def telegram_adapters(
    source: ConfigurationSource, unconfigured: MessengerPort
) -> tuple[MessengerPort, BotInboxPort | None, BotIdentityPort | None]:
    """The bot of the installation, or the unconfigured messenger while the installation has no token."""
    return telegram_channel(_telegram_settings_of(source).token, unconfigured)
