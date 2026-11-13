from dataclasses import dataclass, field

from autotrading.adapters.configuration.source import ConfigurationSource


@dataclass(frozen=True, slots=True)
class _WorkerSettings:
    url: str
    token: str = field(repr=False)


def _settings_of(source: ConfigurationSource) -> _WorkerSettings:
    """The internal address of the worker and the token generated on the machine (ADR 0021)."""
    return _WorkerSettings(source.value("WORKER_URL"), source.secret("WORKER_TOKEN"))
