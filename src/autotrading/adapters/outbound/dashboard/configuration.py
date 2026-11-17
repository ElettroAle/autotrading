from dataclasses import dataclass
from urllib.parse import urlsplit

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource

DASHBOARD_URL = "DASHBOARD_URL"
WEB_SCHEMES = frozenset({"https", "http"})


@dataclass(frozen=True, slots=True)
class _DashboardSettings:
    """Where the users open the dashboard of the installation, if it has one: no secret (ADR 0117)."""

    url: str | None


def _settings_of(source: ConfigurationSource) -> _DashboardSettings:
    url = source.optional(DASHBOARD_URL)
    if url is None:
        return _DashboardSettings(None)
    parts = urlsplit(url)
    if parts.scheme not in WEB_SCHEMES or not parts.netloc:
        raise InvalidConfigurationError(DASHBOARD_URL)
    return _DashboardSettings(url.rstrip("/"))
