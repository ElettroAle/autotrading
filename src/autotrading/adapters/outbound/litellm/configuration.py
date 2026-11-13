from dataclasses import dataclass, field

from autotrading.adapters.configuration.source import ConfigurationSource


@dataclass(frozen=True, slots=True)
class _LiteLlmSettings:
    """Where the proxy of the installation is and the master key that reaches it, from a mounted file."""

    url: str
    master_key: str = field(repr=False)


def _settings_of(source: ConfigurationSource) -> _LiteLlmSettings:
    return _LiteLlmSettings(source.value("LITELLM_URL"), source.secret("LITELLM_MASTER_KEY"))
