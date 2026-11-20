from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from autotrading.application.sources.collect_cycle_source import (
    CollectCycleSourceUseCase,
    SourceCredentialServices,
)
from autotrading.application.sources.errors import SourceCredentialsRejectedError
from autotrading.application.sources.list_sources import SourceSystems
from autotrading.domain.sources.errors import SourceAdapterNotAvailableError, SourceAdapterNotConfiguredError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_adapter_declaration import SourceConfigurationField
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.sources.source_sample import CycleReference
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.source_credentials import (
    FakeSourceCredentialsRejectionNoticeAdapter,
    FakeSourceSecretsOpenerAdapter,
    FakeSourceSecretsSealerAdapter,
    InMemorySourceCredentialsRepositoryAdapter,
    SourceCredentialsStore,
    SourceSecretsVault,
)
from tests.fakes.source_readers import InMemorySampleRepositoryAdapter
from tests.fakes.sources import UPDATED_AT, FakeNewsAdapter, FakeSentimentAdapter

PLANNED_AT = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
ASKED_AT = datetime(2026, 11, 13, 10, 0, 2, tzinfo=UTC)
TENANT = TenantId(uuid4())
PAID = "Pagato"
API_KEY = SourceConfigurationField("api_key", "Chiave API", secret=True)
ACCOUNT = SourceConfigurationField("account", "Account", secret=False)


@dataclass(frozen=True, slots=True)
class Ask:
    source: str
    adapter: str
    cycle_minutes: int = 15
    flow_id: UUID = field(default_factory=uuid4)
    planned_at: datetime = PLANNED_AT
    weight: int = 7
    parameters: dict[str, int] = field(default_factory=dict)
    assets: tuple[str, ...] = ("BTC",)
    asked_at: datetime = ASKED_AT


class World:
    def __init__(self) -> None:
        self.market = FakeMarketDataAdapter()
        self.samples = InMemorySampleRepositoryAdapter()
        self.alternative_me = FakeSentimentAdapter("alternative.me", SentimentIndex(72, "Greed", UPDATED_AT))
        self.coinmarketcap = FakeSentimentAdapter("CoinMarketCap", SentimentIndex(55, "Neutral", UPDATED_AT))
        self.paid = FakeSentimentAdapter(
            PAID, SentimentIndex(40, "Fear", UPDATED_AT), configuration_fields=(API_KEY, ACCOUNT)
        )
        self.vault: SourceSecretsVault = {}
        self.credentials = InMemorySourceCredentialsRepositoryAdapter(SourceCredentialsStore(), TENANT)
        self.notice = FakeSourceCredentialsRejectionNoticeAdapter()
        systems = SourceSystems(
            (self.alternative_me, self.coinmarketcap, self.paid),
            FakeNewsAdapter(),
            FakePriceHistoryAdapter(),
            FakePriceForecasterAdapter(),
            self.market,
            (),
            (),
            (),
        )
        services = SourceCredentialServices(self.credentials, FakeSourceSecretsOpenerAdapter(self.vault), self.notice)
        self.collect = CollectCycleSourceUseCase(systems, InMemoryForecastRepositoryAdapter(), self.samples, services)

    def configure_paid(self) -> None:
        sealed = FakeSourceSecretsSealerAdapter(TENANT, self.vault).seal(PAID, {"api_key": "K-PAID"})
        self.credentials.save(SourceCredentials(TENANT, PAID, {"account": "anna"}, sealed))


def test_the_source_is_collected_with_its_adapter_and_the_weight_of_the_flow_and_recorded_for_the_cycle() -> None:
    world = World()
    ask = Ask(SENTIMENT.name, "alternative.me")

    collected = world.collect.execute(ask)

    assert (collected.source, collected.adapter, collected.weight) == (SENTIMENT.name, "alternative.me", 7)
    assert world.samples.samples == list(collected.samples)
    assert {sample.cycle for sample in collected.samples} == {CycleReference(ask.flow_id, PLANNED_AT)}


def test_each_adapter_of_the_sentiment_reads_its_own_provider() -> None:
    world = World()

    first = world.collect.execute(Ask(SENTIMENT.name, "alternative.me"))
    second = world.collect.execute(Ask(SENTIMENT.name, "CoinMarketCap"))

    assert [sample.values["valore"] for sample in (*first.samples, *second.samples)] == ["72", "55"]


@pytest.mark.parametrize(
    ("source", "adapter"),
    [(INDICATORS.name, "Hyperliquid"), (PIVOTS.name, "Hyperliquid"), (FORECAST.name, "Prophet"), (NEWS.name, "RSS")],
)
def test_every_source_is_read_by_the_adapter_it_declares(source: str, adapter: str) -> None:
    collected = World().collect.execute(Ask(source, adapter))

    assert (collected.source, collected.adapter) == (source, adapter)


def test_an_adapter_the_platform_does_not_offer_is_not_available() -> None:
    with pytest.raises(SourceAdapterNotAvailableError):
        World().collect.execute(Ask(SENTIMENT.name, "altro"))


def test_the_indicators_read_the_candles_of_the_cycle_interval_of_the_flow() -> None:
    hourly, quarterly = World(), World()

    hourly.collect.execute(Ask(INDICATORS.name, "Hyperliquid", cycle_minutes=60))
    quarterly.collect.execute(Ask(INDICATORS.name, "Hyperliquid", cycle_minutes=15))

    assert {label for _, label, _ in hourly.market.requests} != {label for _, label, _ in quarterly.market.requests}


def test_an_adapter_without_configuration_reads_with_no_credentials() -> None:
    world = World()

    world.collect.execute(Ask(SENTIMENT.name, "alternative.me"))

    assert world.alternative_me.received == [{}]


def test_an_adapter_that_needs_configuration_reads_with_the_public_and_the_opened_secret_values() -> None:
    world = World()
    world.configure_paid()

    collected = world.collect.execute(Ask(SENTIMENT.name, PAID))

    assert world.paid.received == [{"account": "anna", "api_key": "K-PAID"}]
    assert [sample.values["valore"] for sample in collected.samples] == ["40"]


def test_an_adapter_not_configured_in_the_cycle_is_absent_with_the_reason_without_being_read() -> None:
    world = World()

    reason = "configura l'adapter Pagato in Impostazioni \u203a Chiavi"
    with pytest.raises(SourceAdapterNotConfiguredError, match=reason):
        world.collect.execute(Ask(SENTIMENT.name, PAID))

    assert world.paid.received == []


def test_credentials_refused_by_the_provider_are_marked_and_told_once_and_the_source_stays_absent() -> None:
    world = World()
    world.configure_paid()
    world.paid.rejects_credentials = True

    for _ in range(2):
        with pytest.raises(SourceCredentialsRejectedError):
            world.collect.execute(Ask(SENTIMENT.name, PAID))

    saved = world.credentials.get(PAID)
    assert saved is not None
    assert saved.rejected_at == ASKED_AT
    assert world.notice.told == [PAID]
    assert world.samples.samples == []
