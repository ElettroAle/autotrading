from dataclasses import dataclass
from datetime import timedelta

from autotrading.domain.accounts.errors import ReconciliationIntervalOutOfRangeError

LOWEST_MINUTES = 1
HIGHEST_MINUTES = 24 * 60
DEFAULT_MINUTES = 5


@dataclass(frozen=True, slots=True)
class ReconciliationInterval:
    """How often, in whole minutes, the periodic check reconciles the account while its flows hold open positions (Bug
    778, ADR intervallo-di-riconciliazione-del-conto).
    """

    minutes: int

    def __post_init__(self) -> None:
        if not LOWEST_MINUTES <= self.minutes <= HIGHEST_MINUTES:
            raise ReconciliationIntervalOutOfRangeError(self.minutes)

    @classmethod
    def default(cls) -> ReconciliationInterval:
        return cls(DEFAULT_MINUTES)

    @classmethod
    def of(cls, minutes: int | None) -> ReconciliationInterval:
        """An interval the user left empty is the default."""
        return cls.default() if minutes is None else cls(minutes)

    @property
    def duration(self) -> timedelta:
        return timedelta(minutes=self.minutes)
