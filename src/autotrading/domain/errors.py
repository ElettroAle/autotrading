from collections.abc import Mapping
from typing import ClassVar


class AutotradingError(Exception):
    """Root of every error the platform raises: each error declares the HTTP status that answers it (ADR 0027)."""

    status_code: ClassVar[int] = 400
    # A permanent error repeats at every cycle until the user acts (R1.2.4); any other error is transient (R1.2.3).
    permanent: ClassVar[bool] = False

    @property
    def details(self) -> Mapping[str, object]:
        return {}


class DomainError(AutotradingError):
    pass
