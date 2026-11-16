from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.accounts.errors import DeviationThresholdOutOfRangeError

LOWEST_PERCENT = Decimal("0.1")
HIGHEST_PERCENT = Decimal(100)
DEFAULT_PERCENT = Decimal(1)


@dataclass(frozen=True, slots=True)
class DeviationThreshold:
    """How far, in percent of the expected balance, the balance read on the exchange may go before the reconciliation
    of the account raises an alarm (R3.3.1).
    """

    percent: Decimal

    def __post_init__(self) -> None:
        if not LOWEST_PERCENT <= self.percent <= HIGHEST_PERCENT:
            raise DeviationThresholdOutOfRangeError(self.percent)

    @classmethod
    def default(cls) -> DeviationThreshold:
        return cls(DEFAULT_PERCENT)
