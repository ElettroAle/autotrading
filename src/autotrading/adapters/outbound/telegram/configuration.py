from dataclasses import dataclass, field

from autotrading.adapters.configuration.source import ConfigurationSource


@dataclass(frozen=True, slots=True)
class _TelegramSettings:
    """The token of the bot of the installation, read from a file mounted read-only; none until it exists (ADR 0035)."""

    token: str | None = field(repr=False)


def _settings_of(source: ConfigurationSource) -> _TelegramSettings:
    return _TelegramSettings(source.optional_secret("TELEGRAM_BOT_TOKEN"))
