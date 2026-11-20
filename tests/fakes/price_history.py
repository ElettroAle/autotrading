from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.price_forecast import PricePoint


@dataclass
class FakePriceHistoryAdapter:
    """The prices of the exchange as the test decides them: a steady series at the finest candles or at the daily ones,
    or a missing asset.
    """

    available_days: int = 90
    spacing: timedelta = timedelta(hours=1)
    prices: dict[str, Decimal] = field(default_factory=dict)
    missing: set[str] = field(default_factory=set)
    requests: list[tuple[str, int]] = field(default_factory=list)
    daily_available_days: int = 1000
    daily_missing: set[str] = field(default_factory=set)
    daily_requests: list[tuple[str, int]] = field(default_factory=list)

    def history(self, asset: str, days: int, now: datetime) -> Sequence[PricePoint]:
        self.requests.append((asset, days))
        self._raise_if_missing(asset)
        return self._series(asset, min(days, self.available_days), self.spacing, now)

    def daily_history(self, asset: str, days: int, now: datetime) -> Sequence[PricePoint]:
        self.daily_requests.append((asset, days))
        if asset in self.daily_missing:
            raise SourceUnavailableError(FORECAST.name)
        self._raise_if_missing(asset)
        # A daily candle closes at midnight: the first one available closes on the first day of the history.
        return self._series(asset, min(days, self.daily_available_days), timedelta(days=1), now, first=0)

    def current_price(self, asset: str) -> Decimal:
        self._raise_if_missing(asset)
        return self.prices[asset]

    def _series(self, asset: str, days: int, spacing: timedelta, now: datetime, first: int = 1) -> list[PricePoint]:
        start = now - timedelta(days=days)
        count = int((now - start) / spacing)
        last = self.prices.get(asset, Decimal(100))
        return [PricePoint(start + spacing * index, last) for index in range(first, first + count)]

    def _raise_if_missing(self, asset: str) -> None:
        if asset in self.missing:
            raise SourceUnavailableError(FORECAST.name)
