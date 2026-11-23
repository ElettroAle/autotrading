from dataclasses import dataclass

from autotrading.domain.errors import AutotradingError


@dataclass(frozen=True, slots=True)
class FailedOrderAttempt:
    """An attempt of the sending of an order of a cycle that failed with an error, the first one being 1: what the
    cycle records of the order sent again (ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo).
    """

    asset: str
    attempt: int
    error_type: str
    message: str

    @classmethod
    def of(cls, asset: str, attempt: int, error: AutotradingError) -> FailedOrderAttempt:
        return cls(asset, attempt, type(error).__name__, str(error))
