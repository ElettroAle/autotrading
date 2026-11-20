import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.domain.accounts.installation_environment import InstallationEnvironment

ENDPOINT = "GRAFANA_OTLP_ENDPOINT"
INSTANCE = "GRAFANA_INSTANCE_ID"
VERSION = "APP_VERSION"
WEB_SCHEMES = frozenset({"https", "http"})
INSTANCE_NUMBER = re.compile(r"[0-9]+")


@dataclass(frozen=True, slots=True)
class _GrafanaCloudSettings:
    """Where and as whom a service exports its telemetry: endpoint and instance are public, the token is a file mounted
    read-only (ADR telemetria-opentelemetry-verso-grafana-cloud).
    """

    endpoint: str
    instance_id: str
    token: str = field(repr=False)
    version: str | None
    environment: InstallationEnvironment


def _settings_of(source: ConfigurationSource) -> _GrafanaCloudSettings | None:
    """None when any of endpoint, instance and token is missing: the telemetry is off and the service starts as ever."""
    endpoint = source.optional(ENDPOINT)
    instance_id = source.optional(INSTANCE)
    token = source.optional_secret("GRAFANA_OTLP_TOKEN")
    if endpoint is None or instance_id is None or token is None:
        return None
    parts = urlsplit(endpoint)
    if parts.scheme not in WEB_SCHEMES or not parts.netloc:
        raise InvalidConfigurationError(ENDPOINT)
    if not INSTANCE_NUMBER.fullmatch(instance_id):
        raise InvalidConfigurationError(INSTANCE)
    return _GrafanaCloudSettings(
        endpoint.rstrip("/"), instance_id, token, source.optional(VERSION), source.environment()
    )
