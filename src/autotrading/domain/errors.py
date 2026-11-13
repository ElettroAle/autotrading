from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ErrorScope:
    """What a permanent error concerns beyond the flow of its cycle: an account, a provider of models, or neither
    (R1.2.4).
    """

    account_id: UUID | None = None
    provider: str | None = None


class AutotradingError(Exception):
    """Root of every error the platform raises: each error declares the HTTP status that answers it (ADR 0027)."""

    status_code: ClassVar[int] = 400
    # A permanent error repeats at every cycle until the user acts (R1.2.4); any other error is transient (R1.2.3).
    permanent: ClassVar[bool] = False

    @property
    def details(self) -> Mapping[str, object]:
        return {}

    @property
    def scope(self) -> ErrorScope:
        """Only the flow of the cycle, unless the error declares an account or a provider (ADR 0082)."""
        return ErrorScope()


class DomainError(AutotradingError):
    pass
