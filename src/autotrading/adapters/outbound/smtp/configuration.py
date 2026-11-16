from dataclasses import dataclass, field, replace

from autotrading.adapters.configuration.errors import InvalidConfigurationError, MissingConfigurationError
from autotrading.adapters.configuration.source import FILE_SUFFIX, ConfigurationSource

SUBMISSION_PORT = 587
HIGHEST_PORT = 65535
HOST = "SMTP_HOST"
PORT = "SMTP_PORT"
SENDER = "SMTP_SENDER"
USERNAME = "SMTP_USERNAME"
PASSWORD = "SMTP_PASSWORD"  # noqa: S105 - the name of the file variable, never the password


@dataclass(frozen=True, slots=True)
class _SmtpSettings:
    """The mail service of the installation; none until the owner chooses one (ADR
    canale-email-delle-notifiche-con-smtp). The password is a file mounted read-only on the worker alone.
    """

    host: str | None
    port: int = SUBMISSION_PORT
    sender: str | None = None
    login: tuple[str, str] | None = field(default=None, repr=False)


def _settings_of(source: ConfigurationSource) -> _SmtpSettings:
    """What the worker needs to send: the plain settings and, with a user, the password of its file."""
    settings = _plain_settings_of(source)
    username = source.optional(USERNAME)
    if settings.host is None or username is None:
        return settings
    password = source.optional_secret(PASSWORD)
    if password is None:
        raise MissingConfigurationError(PASSWORD + FILE_SUFFIX)
    return replace(settings, login=(username, password))


def _plain_settings_of(source: ConfigurationSource) -> _SmtpSettings:
    """What the API needs to know whether the service exists: never the password, which it does not mount."""
    host = source.optional(HOST)
    if host is None:
        return _SmtpSettings(None)
    return _SmtpSettings(host, _port_of(source.optional(PORT)), source.value(SENDER))


def _port_of(text: str | None) -> int:
    if text is None:
        return SUBMISSION_PORT
    if not text.isdigit() or not 0 < int(text) <= HIGHEST_PORT:
        raise InvalidConfigurationError(PORT)
    return int(text)
