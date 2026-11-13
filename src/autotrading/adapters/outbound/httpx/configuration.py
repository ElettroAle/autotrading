from dataclasses import dataclass, field

from autotrading.adapters.configuration.source import ConfigurationSource


@dataclass(frozen=True, slots=True)
class _WorkerSettings:
    url: str
    token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class _TelegramSettings:
    token: str | None = field(repr=False)


def _worker_settings_of(source: ConfigurationSource) -> _WorkerSettings:
    """The internal address of the worker and the token generated on the machine (ADR 0021)."""
    return _WorkerSettings(source.value("WORKER_URL"), source.secret("WORKER_TOKEN"))


def _telegram_settings_of(source: ConfigurationSource) -> _TelegramSettings:
    """The token of the bot is optional: without it the notifications are off (ADR 0035)."""
    return _TelegramSettings(source.optional_secret("TELEGRAM_BOT_TOKEN"))
