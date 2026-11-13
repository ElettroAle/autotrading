from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.news_item import NewsItem
from autotrading.domain.sources.pivot_levels import DailyRange
from autotrading.domain.sources.price_forecast import PriceForecast, PricePoint
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_sample import SourceSample, SourceValue
from autotrading.domain.sources.timeframe import Timeframe


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


class MarketDataPort(Protocol):
    """The public market data of the exchange for an asset, without credentials (R1.3.3, R1.3.4)."""

    def timeframes(self) -> Sequence[Timeframe]:
        """The candle intervals the exchange publishes."""
        ...

    def candles(self, asset: str, timeframe: Timeframe, count: int, now: datetime) -> Sequence[Candle]:
        """The last `count` closed candles of the timeframe, oldest first; fewer when the exchange has less.

        Raises TimeframeNotSupportedError for an interval outside `timeframes()`, SourceUnavailableError.
        """
        ...

    def snapshot(self, asset: str) -> MarketSnapshot:
        """Mark price, mid price, open interest and funding rate now. Raises SourceUnavailableError."""
        ...

    def previous_day(self, asset: str, now: datetime) -> DailyRange:
        """High, low and close of the UTC day before `now`. Raises SourceUnavailableError."""
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


@dataclass(frozen=True, slots=True)
class SourceRequest:
    """What a reader of a source is asked: for an asset, or for the whole market when asset is None (R1.3.2)."""

    flow_id: UUID
    asset: str | None
    settings: Mapping[str, int]
    now: datetime


class SourceReaderPort(Protocol):
    """Reads one source of the catalog with the parameters of the flow (R1.3.2)."""

    def execute(self, command: SourceRequest) -> Sequence[SourceValue]:
        """The values read, each with its reference instant. Raises a typed error when the source has no data."""
        ...


class SampleRepositoryPort(Protocol):
    """Bound to the tenant of the flow: the values its cycles collected (R1.3.8)."""

    def add(self, samples: Sequence[SourceSample]) -> None: ...


class CycleSourceAskPort(Protocol):
    """An active source of a flow, as the cycle of the flow asks it (R1.3.2): who asks, for what and with what."""

    @property
    def flow_id(self) -> UUID: ...

    @property
    def planned_at(self) -> datetime: ...

    @property
    def source(self) -> str: ...

    @property
    def weight(self) -> int: ...

    @property
    def parameters(self) -> Mapping[str, int]: ...

    @property
    def assets(self) -> tuple[str, ...]: ...

    @property
    def cycle_minutes(self) -> int: ...

    @property
    def asked_at(self) -> datetime: ...
