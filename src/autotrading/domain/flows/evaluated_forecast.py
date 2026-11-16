from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class EvaluatedForecast:
    """A price forecast of the flow whose horizon has expired, with the actual price of the asset at that instant, or
    none when it was never read (R1.3.5, R3.6.1).

    Without an actual price above zero there is nothing to measure the forecast against: it is not evaluable.
    """

    asset: str
    horizon_minutes: int
    expires_at: datetime
    predicted_price: Decimal
    actual_price: Decimal | None

    @property
    def evaluable(self) -> bool:
        return self.absolute_error is not None

    @property
    def absolute_error(self) -> Decimal | None:
        if self.actual_price is None or self.actual_price <= 0:
            return None
        return abs(self.predicted_price - self.actual_price)

    @property
    def percent_error(self) -> Decimal | None:
        """The absolute error over the actual price, in percent."""
        error = self.absolute_error
        if error is None or self.actual_price is None:
            return None
        return error / self.actual_price * HUNDRED
