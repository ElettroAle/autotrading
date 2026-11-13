from dataclasses import dataclass, field

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.domain.accounts.installation_environment import InstallationEnvironment


@dataclass(frozen=True, slots=True)
class _ApiSettings:
    version: str
    environment: InstallationEnvironment


@dataclass(frozen=True, slots=True)
class _ApiLoginSettings:
    client_id: str
    scope: str


@dataclass(frozen=True, slots=True)
class _WorkerApiSettings:
    token: str = field(repr=False)


def _api_settings_of(source: ConfigurationSource) -> _ApiSettings:
    return _ApiSettings(source.value("APP_VERSION"), source.environment())


def _login_settings_of(source: ConfigurationSource) -> _ApiLoginSettings:
    """The client the OpenAPI page logs in with (ADR 0016, ADR 0073)."""
    return _ApiLoginSettings(source.value("AUTH_CLIENT_ID"), source.value("AUTH_SCOPE"))


def _worker_api_settings_of(source: ConfigurationSource) -> _WorkerApiSettings:
    """The token generated on the machine: only the API holds it as well (ADR 0021)."""
    return _WorkerApiSettings(source.secret("WORKER_TOKEN"))
