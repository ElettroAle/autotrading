from dataclasses import dataclass

from autotrading.domain.errors import AutotradingError


@dataclass(frozen=True, slots=True)
class FailedOrderAttempt:
    """An attempt of a call of the orders of a cycle that failed with an error, the first one being 1: what the cycle
    records of the order or the protection sent again, named by its asset, and of the access to the account, which has
    none (ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo, ADR protezioni-ritentate-nel-ciclo).
    """

    asset: str | None
    attempt: int
    error_type: str
    message: str

    @classmethod
    def of(cls, asset: str | None, attempt: int, error: AutotradingError) -> FailedOrderAttempt:
        return cls(asset, attempt, type(error).__name__, str(error))
