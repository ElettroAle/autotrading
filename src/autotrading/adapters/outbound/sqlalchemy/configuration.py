from dataclasses import dataclass, field

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource

DEFAULT_PORT = 5432
HIGHEST_PORT = 65535
PORT = "DATABASE_PORT"


@dataclass(frozen=True, slots=True)
class _SqlAlchemySettings:
    host: str
    port: int
    name: str
    user: str
    password: str = field(repr=False)


def _settings_of(source: ConfigurationSource) -> _SqlAlchemySettings:
    return _SqlAlchemySettings(
        host=source.value("DATABASE_HOST"),
        port=_port_of(source.optional(PORT)),
        name=source.value("DATABASE_NAME"),
        user=source.value("DATABASE_USER"),
        password=source.secret("DATABASE_PASSWORD"),
    )


def _port_of(text: str | None) -> int:
    if text is None:
        return DEFAULT_PORT
    if not text.isdigit() or not 0 < int(text) <= HIGHEST_PORT:
        raise InvalidConfigurationError(PORT)
    return int(text)
