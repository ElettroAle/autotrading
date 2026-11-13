from enum import StrEnum

from autotrading.domain.accounts.errors import UndeclaredEnvironmentError, UnsupportedEnvironmentError


class InstallationEnvironment(StrEnum):
    """The installations the platform knows: dev on the test networks, prod on the real ones (ADR 0087)."""

    DEV = "dev"
    PROD = "prod"

    @classmethod
    def declared(cls, text: str | None) -> InstallationEnvironment:
        environment = (text or "").strip()
        if not environment:
            raise UndeclaredEnvironmentError
        supported = tuple(member.value for member in cls)
        if environment not in supported:
            raise UnsupportedEnvironmentError(environment, supported)
        return cls(environment)
