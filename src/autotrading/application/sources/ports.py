from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from autotrading.domain.sources.news_item import NewsItem
from autotrading.domain.sources.price_forecast import PriceForecast, PricePoint
from autotrading.domain.sources.sentiment_index import SentimentIndex


class SentimentPort(Protocol):
    """One Fear & Greed provider: each sentiment source of the catalog has its own adapter (R1.3.6)."""

    def read_index(self) -> SentimentIndex:
        """The current index of the provider; raises SourceUnavailableError when it cannot be read."""
        ...


class NewsPort(Protocol):
    """The crypto outlets the news source reads from (R1.3.7)."""

    def read_latest(self) -> Sequence[NewsItem]:
        """The stories the outlets publish now, in any order; raises SourceUnavailableError when none answers."""
        ...


class PriceHistoryPort(Protocol):
    """The closing prices of the exchange for an asset (R1.3.5)."""

    def history(self, asset: str, days: int, now: datetime) -> Sequence[PricePoint]:
        """The prices of the last `days` days, at the finest interval the exchange keeps for that span.

        Fewer days when the exchange has less history. Raises SourceUnavailableError.
        """
        ...

    def current_price(self, asset: str) -> Decimal:
        """The price of the asset now. Raises SourceUnavailableError."""
        ...


class ForecastRepositoryPort(Protocol):
    """Bound to the tenant of the request: the forecasts of its flows (R1.3.5)."""

    def add(self, forecast: PriceForecast) -> None: ...

    def expired_without_actual(self, now: datetime) -> list[PriceForecast]:
        """The forecasts whose horizon has expired and that have no actual price yet."""
        ...

    def record_actual(self, forecast: PriceForecast) -> None:
        """Saves the actual price of a forecast already added."""
        ...
