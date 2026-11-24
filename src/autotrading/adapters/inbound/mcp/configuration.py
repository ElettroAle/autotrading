from dataclasses import dataclass

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource

PUBLIC_URL = "MCP_PUBLIC_URL"
SECURE_SCHEME = "https://"


@dataclass(frozen=True, slots=True)
class _McpSettings:
    version: str
    public_url: str
    issuer: str
    scope: str


def _mcp_settings_of(source: ConfigurationSource) -> _McpSettings:
    """The public address of the server, the resource its metadata declare, is HTTPS on the tailnet (ADR 0013); the
    issuer and the scope are those of the API (ADR 0016).
    """
    public_url = source.value(PUBLIC_URL)
    if not public_url.startswith(SECURE_SCHEME):
        raise InvalidConfigurationError(PUBLIC_URL)
    return _McpSettings(
        source.value("APP_VERSION"), public_url, source.value("AUTH_ISSUER"), source.value("AUTH_SCOPE")
    )
