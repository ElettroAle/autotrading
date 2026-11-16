from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

HUNDRED = Decimal(100)
ZERO = Decimal(0)
DEVIATION_PRECISION = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class BalanceComparison:
    """The balance read on the exchange against the one the last reference and what happened since explain (R3.3.1).

    The read balance leaves out the unrealized PnL of the open positions, which no execution explains while they stay
    open.
    """

    expected: Decimal
    read: Decimal
    compared_at: datetime

    @property
    def difference(self) -> Decimal:
        return self.read - self.expected

    @property
    def deviation_percent(self) -> Decimal:
        """How far the read balance is from the expected one, either way, in percent of the expected balance."""
        if self.expected == ZERO:
            return ZERO if self.difference == ZERO else HUNDRED
        return (abs(self.difference) / abs(self.expected) * HUNDRED).quantize(DEVIATION_PRECISION)

    def exceeds(self, threshold_percent: Decimal) -> bool:
        # Measured without dividing: with nothing expected, any difference is beyond every threshold.
        return abs(self.difference) * HUNDRED > threshold_percent * abs(self.expected)
