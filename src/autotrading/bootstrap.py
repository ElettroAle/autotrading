import os
from collections.abc import Mapping

from fastapi import FastAPI

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.domain.errors import AutotradingError

SUPPORTED_ENVIRONMENTS = ("dev", "prod")


class MissingConfigurationError(AutotradingError):
    def __init__(self, name: str) -> None:
        super().__init__(f"configurazione mancante: {name}")
        self.name = name


class UndeclaredEnvironmentError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("ambiente non dichiarato")


class UnsupportedEnvironmentError(AutotradingError):
    def __init__(self, environment: str) -> None:
        super().__init__("ambiente non ammesso: sono ammessi " + " e ".join(SUPPORTED_ENVIRONMENTS))
        self.environment = environment


def create_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    health = HealthReport(
        version=_required(configuration, "APP_VERSION"),
        environment=_environment(configuration),
    )
    return create_api(health)


def _required(configuration: Mapping[str, str], name: str) -> str:
    value = configuration.get(name, "").strip()
    if not value:
        raise MissingConfigurationError(name)
    return value


def _environment(configuration: Mapping[str, str]) -> str:
    environment = configuration.get("APP_ENVIRONMENT", "").strip()
    if not environment:
        raise UndeclaredEnvironmentError
    if environment not in SUPPORTED_ENVIRONMENTS:
        raise UnsupportedEnvironmentError(environment)
    return environment
