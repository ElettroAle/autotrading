from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.price_forecast import PricePoint


@dataclass
class FakePriceHistoryAdapter:
    """The prices of the exchange as the test decides them: a steady series, or a missing asset."""

    available_days: int = 90
    spacing: timedelta = timedelta(hours=1)
    prices: dict[str, Decimal] = field(default_factory=dict)
    missing: set[str] = field(default_factory=set)
    requests: list[tuple[str, int]] = field(default_factory=list)

    def history(self, asset: str, days: int, now: datetime) -> Sequence[PricePoint]:
        self.requests.append((asset, days))
        self._raise_if_missing(asset)
        start = now - timedelta(days=min(days, self.available_days))
        count = int((now - start) / self.spacing)
        last = self.prices.get(asset, Decimal(100))
        return [PricePoint(start + self.spacing * index, last) for index in range(1, count + 1)]

    def current_price(self, asset: str) -> Decimal:
        self._raise_if_missing(asset)
        return self.prices[asset]

    def _raise_if_missing(self, asset: str) -> None:
        if asset in self.missing:
            raise SourceUnavailableError(FORECAST.name)
