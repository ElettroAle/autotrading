from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.key_expiry import KeyExpiry
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.news_item import NewsItem
from autotrading.domain.sources.pivot_levels import DailyRange
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast, PriceHistory, PricePoint
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.social_snapshot import SocialSnapshot
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.sources.source_sample import SourceSample, SourceValue
from autotrading.domain.sources.source_trial import SourceTrial
from autotrading.domain.sources.timeframe import Timeframe
from autotrading.domain.sources.volume_snapshot import UnlistedAsset, VolumeSnapshot
from autotrading.domain.sources.whale_transfer import WhaleTransfer


class SentimentPort(Protocol):
    """One Fear & Greed provider: each one is an adapter of the sentiment source (R1.3.6, R4.1.1)."""

    def declaration(self) -> SourceAdapterDeclaration:
        """What the adapter declares of itself, without asking the provider (R4.1.1)."""
        ...

    def read_index(self, credentials: Mapping[str, str]) -> SentimentIndex:
        """The current index of the provider, read with the credentials the tenant gave the adapter, none when it
        declares no field (R4.1.2); raises SourceUnavailableError when it cannot be read and
        SourceCredentialsRejectedError when the provider refuses the credentials.
        """
        ...


class NewsPort(Protocol):
    """The crypto outlets the news source reads from (R1.3.7)."""

    def declaration(self) -> SourceAdapterDeclaration:
        """What the adapter declares of itself, without asking the outlets (R4.1.1)."""
        ...

    def read_latest(self) -> Sequence[NewsItem]:
        """The stories the outlets publish now, in any order; raises SourceUnavailableError when none answers."""
        ...


class WhaleTransfersPort(Protocol):
    """One provider of the large on-chain transfers: each one is an adapter of the whale source (R5.1.1, ADR
    fonte-whale-con-adapter-arkham)."""

    def declaration(self) -> SourceAdapterDeclaration:
        """What the adapter declares of itself, its threshold of value included, without asking the provider
        (R4.1.1)."""
        ...

    def transfers(
        self, since: datetime, until: datetime, minimum_usd: int, credentials: Mapping[str, str]
    ) -> Sequence[WhaleTransfer]:
        """The transfers between the two instants worth at least the threshold, in dollars, in any order, read with the
        credentials the tenant gave the adapter (R4.1.2); raises SourceUnavailableError when they cannot be read and
        SourceCredentialsRejectedError when the provider refuses the credentials.
        """
        ...


class VolumesPort(Protocol):
    """One exchange that publishes its market data: each one is an adapter of the volumes source (R5.1.2, ADR
    fonte-volumi-con-adapter-binance)."""

    def declaration(self) -> SourceAdapterDeclaration:
        """What the adapter declares of itself, without asking the exchange (R4.1.1)."""
        ...

    def snapshot(self, asset: str, interval_minutes: int) -> VolumeSnapshot | UnlistedAsset:
        """The volume of the last 24 hours, the aggressive trades of the last interval of the cycle and the order book
        of the asset now; UnlistedAsset when the exchange does not list it. Raises SourceUnavailableError when they
        cannot be read.
        """
        ...


class SocialPort(Protocol):
    """One provider of what is said of the assets on the social networks: each one is an adapter of the social source
    (R5.1.3, ADR fonte-social-con-adapter-lunarcrush)."""

    def declaration(self) -> SourceAdapterDeclaration:
        """What the adapter declares of itself, its number of posts included, without asking the provider (R4.1.1)."""
        ...

    def snapshot(self, asset: str, posts: int, credentials: Mapping[str, str]) -> SocialSnapshot:
        """The sentiment, the mentions and the interactions of the last 24 hours and at least the number of posts asked
        of the most influential creators, the most relevant first, read with the credentials the tenant gave the
        adapter (R4.1.2); raises SourceUnavailableError when they cannot be read and SourceCredentialsRejectedError
        when the provider refuses the credentials.
        """
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

    def declaration(self) -> SourceAdapterDeclaration:
        """What the adapter of the indicators and of the pivots declares of itself, without asking the exchange
        (R4.1.1).
        """
        ...

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


class PriceForecasterPort(Protocol):
    """The model that forecasts the price of an asset from its history (R1.3.5, ADR 0107)."""

    def declaration(self) -> SourceAdapterDeclaration:
        """What the adapter of the forecast declares of itself, without asking the model (R4.1.1)."""
        ...

    def predict(
        self, asset: str, history: PriceHistory, horizons: tuple[ForecastHorizon, ...]
    ) -> Mapping[ForecastHorizon, Decimal]:
        """The predicted price at every horizon after the last point; SourceUnavailableError when it does not answer."""
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
    """What a reader of a source is asked: for an asset, or for the whole market when asset is None (R1.3.2).

    A trial asks it outside every flow, so nothing it reads is recorded (R6.3.1).
    """

    flow_id: UUID | None
    asset: str | None
    settings: Mapping[str, int]
    now: datetime
    # The values the tenant gave the adapter, secrets included: only the worker opens them, and none appears in a
    # log or in the record of the cycle (R4.1.2).
    credentials: Mapping[str, str] = field(default_factory=dict, repr=False)


class SourceReaderPort(Protocol):
    """Reads one adapter of a source of the catalog with the parameters of the flow (R1.3.2, R4.1.1)."""

    def execute(self, command: SourceRequest) -> Sequence[SourceValue]:
        """The values read, each with its reference instant. Raises a typed error when the source has no data."""
        ...


class CycleSourceDatumPort(Protocol):
    """A datum of an adapter of an active source in the context of a cycle, as the flows hand it over (R4.1.1)."""

    @property
    def source(self) -> str: ...

    @property
    def adapter(self) -> str: ...

    @property
    def asset(self) -> str | None: ...

    @property
    def values(self) -> Mapping[str, str]: ...


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
    def adapter(self) -> str: ...

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


class SourceSecretsSealerPort(Protocol):
    """Bound to the tenant of the request: the sealed text names tenant and adapter (R4.1.2, ADR
    credenziali-degli-adapter-delle-fonti)."""

    def seal(self, adapter: str, secrets: Mapping[str, str]) -> SealedSourceSecrets: ...


class SourceSecretsOpenerPort(Protocol):
    """In the worker only: the private key of the installation never reaches the API (ADR 0007, R4.1.2)."""

    def open(self, credentials: SourceCredentials) -> Mapping[str, str]:
        """The secret values; raises SourceSecretsNotOpenedError when the sealed text is not of the tenant and adapter
        of the credentials."""
        ...


@dataclass(frozen=True, slots=True)
class SourceCredentialsRegistration:
    """The credentials of an adapter with the instant of their last configuration (R4.1.2)."""

    credentials: SourceCredentials
    registered_at: datetime


class SourceCredentialsRepositoryPort(Protocol):
    """Bound to the tenant of the request: it never sees the credentials of another tenant (R4.1.2)."""

    def registrations(self) -> tuple[SourceCredentialsRegistration, ...]:
        """The credentials of the tenant, by adapter, each with the instant they were saved."""
        ...

    def get(self, adapter: str) -> SourceCredentials | None: ...

    def save(self, credentials: SourceCredentials) -> None:
        """Adds the credentials of the adapter, or puts them in place of the saved ones."""
        ...

    def remove(self, adapter: str) -> None:
        """Raises SourceCredentialsNotFoundError when the tenant gave the adapter no credentials."""
        ...

    def set_expiry(self, adapter: str, expiry: KeyExpiry | None) -> None:
        """Keeps the expiry, none to forget it; raises SourceCredentialsNotFoundError without credentials (R6.2.2)."""
        ...

    def mark_rejected(self, adapter: str, at: datetime) -> bool:
        """Keeps the instant the provider refused the credentials; False when they were already refused, or are
        missing, so the user is told once until they are replaced."""
        ...


class SourceCredentialsRejectionNoticePort(Protocol):
    """Tells the tenant the provider refused the credentials of an adapter: it is NotifySourceCredentialsRejectedUseCase
    of the notifications (R4.1.2)."""

    def execute(self, adapter: str) -> None: ...


class ConcurrentCallsPort(Protocol):
    """The calls of the cycle, which wait for a source only up to its wait (R1.2.5)."""

    def call_within[R](self, call: Callable[[], R], seconds: float) -> R:
        """The answer of the call; a call still running at the end of the wait is abandoned and raises
        SourceUnansweredError, a call that fails with an error of the project raises it."""
        ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class TrialIntervalPort(Protocol):
    """The cycle a trial reads as: the interval of a flow that names none and the wait of its sources (R6.3.1)."""

    @property
    def minutes(self) -> int: ...

    @property
    def source_wait(self) -> timedelta: ...


class SourceTrialPort(Protocol):
    """Bound to the tenant of the request: tries an adapter of a source now (R6.3.1, ADR
    prova-di-un-adapter-di-fonte-nel-worker).

    Only the worker opens the credentials of the adapters: in the API it is the client that asks the worker to run
    TrySourceAdapterUseCase. A source that fails is the outcome of the trial, not an error.
    """

    def try_adapter(self, source: str, adapter: str, asset: str | None, parameters: Mapping[str, int]) -> SourceTrial:
        """Raises SourceTrialWorkerUnavailableError when the worker cannot be reached or answers in another shape."""
        ...
