from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.errors import InvalidDefaultStopLossError, InvalidDefaultTakeProfitError

MIN_DEFAULT_STOP_LOSS = Decimal("0.1")
MAX_DEFAULT_STOP_LOSS = Decimal(50)
DEFAULT_STOP_LOSS = Decimal(5)


@dataclass(frozen=True, slots=True)
class ProtectionDefaults:
    """The stop loss and take profit of every opening of the flow where the agent gives no level, as a distance in
    percent from the entry price (R3.1.2).

    The stop loss is mandatory, from 0.1 to 50, 5 unless the user says otherwise; the take profit is optional and above
    0 when present.
    """

    stop_loss_percent: Decimal = DEFAULT_STOP_LOSS
    take_profit_percent: Decimal | None = None

    @classmethod
    def of(cls, stop_loss_percent: Decimal | None, take_profit_percent: Decimal | None) -> ProtectionDefaults:
        """The defaults the user gave, with the stop loss of the platform where none is given."""
        stop = DEFAULT_STOP_LOSS if stop_loss_percent is None else stop_loss_percent
        return cls(stop, take_profit_percent)

    def __post_init__(self) -> None:
        stop = self.stop_loss_percent
        if not stop.is_finite() or not MIN_DEFAULT_STOP_LOSS <= stop <= MAX_DEFAULT_STOP_LOSS:
            raise InvalidDefaultStopLossError
        target = self.take_profit_percent
        if target is not None and (not target.is_finite() or target <= 0):
            raise InvalidDefaultTakeProfitError
