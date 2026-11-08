import os
from collections.abc import Mapping

from fastapi import FastAPI

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.domain.errors import AutotradingError


class MissingConfigurationError(AutotradingError):
    def __init__(self, name: str) -> None:
        super().__init__(f"configurazione mancante: {name}")
        self.name = name


def create_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    health = HealthReport(
        version=_required(configuration, "APP_VERSION"),
        environment=_required(configuration, "APP_ENVIRONMENT"),
    )
    return create_api(health)


def _required(configuration: Mapping[str, str], name: str) -> str:
    value = configuration.get(name, "").strip()
    if not value:
        raise MissingConfigurationError(name)
    return value
