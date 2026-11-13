from dataclasses import dataclass

from autotrading.adapters.configuration.source import ConfigurationSource


@dataclass(frozen=True, slots=True)
class _OidcSettings:
    issuer: str
    audience: str


def _settings_of(source: ConfigurationSource) -> _OidcSettings | None:
    """Without an issuer the installation has no login yet: the protected functions answer not configured."""
    issuer = source.optional("AUTH_ISSUER")
    if issuer is None:
        return None
    return _OidcSettings(issuer, source.value("AUTH_AUDIENCE"))
