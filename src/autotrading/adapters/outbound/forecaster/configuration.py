from dataclasses import dataclass

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.forecaster.price_forecast import TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _ForecasterSettings:
    """How the worker reaches the forecaster: its internal address, no secret (ADR 0107)."""

    url: str
    timeout_seconds: float = TIMEOUT_SECONDS


def _settings_of(source: ConfigurationSource) -> _ForecasterSettings:
    return _ForecasterSettings(source.value("FORECASTER_URL"))
