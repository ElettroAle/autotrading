from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

# The codes of an external system that the user alone can clear (credentials, permission, credit) and those that pass
# by themselves (rate limit, server): the error the cause travels with does not change them
# (ADR permanenza-decisa-dall-errore-base).
BLOCKING_CODES = frozenset({401, 402, 403})
TOO_MANY_REQUESTS = 429
SERVER_CODES = range(500, 600)


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
    # What the error is when its cause carries no code that decides: a permanent error repeats at every cycle until
    # the user acts (R1.2.4), any other error is transient (R1.2.3).
    declared_permanent: ClassVar[bool] = False

    @property
    def permanent(self) -> bool:
        """Decided by the code of the external system kept in the cause, else declared by the error
        (ADR permanenza-decisa-dall-errore-base).
        """
        code = self._external_code()
        if code in BLOCKING_CODES:
            return True
        if code == TOO_MANY_REQUESTS or code in SERVER_CODES:
            return False
        return self.declared_permanent

    @property
    def details(self) -> Mapping[str, object]:
        return {}

    @property
    def scope(self) -> ErrorScope:
        """Only the flow of the cycle, unless the error declares an account or a provider (ADR 0082)."""
        return ErrorScope()

    def _external_code(self) -> int | None:
        """The nearest code an external system answered with along the causes; the status of an error of the project
        is the answer of the platform, never of an external system.
        """
        cause = self.__cause__
        seen: set[int] = set()
        while cause is not None and id(cause) not in seen:
            seen.add(id(cause))
            code = None if isinstance(cause, AutotradingError) else _code_of(cause)
            if code is not None:
                return code
            cause = cause.__cause__
        return None


def _code_of(cause: BaseException) -> int | None:
    """Read by name, as the libraries of the adapters name it: on the error or on the response it carries."""
    code = getattr(cause, "status_code", None)
    if code is None:
        code = getattr(getattr(cause, "response", None), "status_code", None)
    return code if isinstance(code, int) else None


class DomainError(AutotradingError):
    pass
