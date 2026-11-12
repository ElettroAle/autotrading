import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from uuid import UUID

from autotrading.domain.sources.errors import InsufficientHistoryError, InvalidPriceForecastError
from autotrading.domain.sources.holt_forecast import MINIMUM_POINTS, holt_forecast

DAY = timedelta(days=1)
HUNDRED = Decimal(100)
PERCENT_PLACES = Decimal("0.01")
# The forecast keeps two more decimals than the exchange gives: enough to see a change, not a false precision.
EXTRA_PLACES = 2


class ForecastHorizon(Enum):
    """The two horizons of R1.3.5, with their label for the context of the agent."""

    MINUTES_15 = (15, "15 minuti")
    HOUR_1 = (60, "1 ora")

    def __init__(self, minutes: int, label: str) -> None:
        self.minutes = minutes
        self.label = label

    @property
    def length(self) -> timedelta:
        return timedelta(minutes=self.minutes)


@dataclass(frozen=True, slots=True)
class PricePoint:
    """A closing price of the exchange at one instant."""

    at: datetime
    price: Decimal


@dataclass(frozen=True, slots=True)
class PriceHistory:
    """The prices of an asset over the depth the flow asked for, or over the shorter span the exchange has."""

    points: tuple[PricePoint, ...]
    requested_days: int
    now: datetime

    def __post_init__(self) -> None:
        if len(self.points) < MINIMUM_POINTS:
            raise InsufficientHistoryError(MINIMUM_POINTS, len(self.points))

    @property
    def last_price(self) -> Decimal:
        return self.points[-1].price

    @property
    def spacing(self) -> timedelta:
        return (self.points[-1].at - self.points[0].at) / (len(self.points) - 1)

    @property
    def shortened(self) -> bool:
        """True when the exchange has less history than requested, by more than one sampling interval."""
        return self.now - self.points[0].at < self.requested_days * DAY - self.spacing

    @property
    def days(self) -> int:
        if not self.shortened:
            return self.requested_days
        return max(1, math.ceil((self.now - self.points[0].at) / DAY))


@dataclass(frozen=True, slots=True)
class PriceForecast:
    """A forecast of the flow for one asset and horizon, then the actual price once the horizon expires (R1.3.5)."""

    flow_id: UUID
    asset: str
    horizon: ForecastHorizon
    made_at: datetime
    last_price: Decimal
    predicted_price: Decimal
    history_days: int
    shortened: bool
    actual_price: Decimal | None = None

    def __post_init__(self) -> None:
        if self.made_at.tzinfo is None or self.last_price <= 0:
            raise InvalidPriceForecastError

    @classmethod
    def of(cls, flow_id: UUID, asset: str, history: PriceHistory, horizon: ForecastHorizon) -> PriceForecast:
        steps = Decimal(horizon.length / history.spacing)
        predicted = holt_forecast([point.price for point in history.points], steps)
        return cls(
            flow_id,
            asset,
            horizon,
            history.now,
            history.last_price,
            predicted.quantize(_places_of(history.last_price)),
            history.days,
            history.shortened,
        )

    @property
    def change_percent(self) -> Decimal:
        return ((self.predicted_price - self.last_price) / self.last_price * HUNDRED).quantize(PERCENT_PLACES)

    @property
    def expires_at(self) -> datetime:
        return self.made_at + self.horizon.length

    def with_actual(self, price: Decimal) -> PriceForecast:
        return replace(self, actual_price=price)


def _places_of(price: Decimal) -> Decimal:
    exponent = price.as_tuple().exponent
    if not isinstance(exponent, int):
        raise InvalidPriceForecastError
    return Decimal(1).scaleb(min(exponent, 0) - EXTRA_PLACES)


def history_of(points: Sequence[PricePoint], requested_days: int, now: datetime) -> PriceHistory:
    """The points in time order: the exchange may answer in pages."""
    return PriceHistory(tuple(sorted(points, key=lambda point: point.at)), requested_days, now)
