from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from autotrading.application.sources.list_sources import SourceSystems
from autotrading.application.sources.open_source_credentials import OpenSourceCredentialsUseCase
from autotrading.application.sources.try_source_adapter import (
    TrialServices,
    TrySourceAdapterCommand,
    TrySourceAdapterUseCase,
)
from autotrading.domain.flows.cycle_interval import DEFAULT_CYCLE_INTERVAL, CycleInterval
from autotrading.domain.sources.errors import (
    SourceAdapterNotAvailableError,
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
    TrialAssetRequiredError,
)
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_adapter_declaration import SourceConfigurationField
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.sources.source_trial import TrialOutcome
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.concurrent_calls import FakeConcurrentCallsAdapter
from tests.fakes.cycles import FakeClockAdapter
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.source_credentials import (
    FakeSourceSecretsOpenerAdapter,
    FakeSourceSecretsSealerAdapter,
    InMemorySourceCredentialsRepositoryAdapter,
    SourceCredentialsStore,
    SourceSecretsVault,
)
from tests.fakes.sources import UPDATED_AT, FakeNewsAdapter, FakeSentimentAdapter

NOW = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)
TENANT = TenantId(uuid4())
PAID = "Pagato"
API_KEY = SourceConfigurationField("api_key", "Chiave API", secret=True)
NOT_CONFIGURED = "configura l'adapter Pagato in Impostazioni \u203a Chiavi"


class World:
    """An adapter of every source of the platform, a paid sentiment that needs a key, and the clock of the worker, which
    moves 250 milliseconds at every reading."""

    def __init__(self, interval: CycleInterval = DEFAULT_CYCLE_INTERVAL) -> None:
        self.market = FakeMarketDataAdapter()
        self.news = FakeNewsAdapter()
        self.paid = FakeSentimentAdapter(PAID, SentimentIndex(40, "Fear", UPDATED_AT), configuration_fields=(API_KEY,))
        self.forecasts = InMemoryForecastRepositoryAdapter()
        self.vault: SourceSecretsVault = {}
        self.credentials = InMemorySourceCredentialsRepositoryAdapter(SourceCredentialsStore(), TENANT)
        self.calls = FakeConcurrentCallsAdapter()
        systems = SourceSystems(
            (FakeSentimentAdapter("alternative.me"), self.paid),
            self.news,
            FakePriceHistoryAdapter(),
            FakePriceForecasterAdapter(),
            self.market,
            (),
            (),
        )
        self.trial = TrySourceAdapterUseCase(
            systems,
            self.forecasts,
            OpenSourceCredentialsUseCase(self.credentials, FakeSourceSecretsOpenerAdapter(self.vault)),
            TrialServices(self.calls, FakeClockAdapter(NOW, timedelta(milliseconds=250)), interval),
        )

    def configure_paid(self) -> None:
        sealed = FakeSourceSecretsSealerAdapter(TENANT, self.vault).seal(PAID, {"api_key": "K-PAID"})
        self.credentials.save(SourceCredentials(TENANT, PAID, {}, sealed))


def test_a_trial_reads_the_values_with_the_instant_of_the_data_and_the_time_of_the_answer() -> None:
    trial = World().trial.execute(TrySourceAdapterCommand("indicatori", "Hyperliquid", "BTC"))

    assert trial.outcome is TrialOutcome.SUCCEEDED
    assert [value.values["prezzo"] for value in trial.values] == ["100"]
    assert trial.data_at == trial.values[0].reference_at
    assert trial.response_milliseconds == 250


def test_the_parameters_not_set_take_their_default_and_those_set_are_read() -> None:
    world = World()

    world.trial.execute(TrySourceAdapterCommand("indicatori", "Hyperliquid", "BTC", {"lunghezza_serie": 20}))
    world.trial.execute(TrySourceAdapterCommand("indicatori", "Hyperliquid", "BTC"))

    short_requests = [count for _, label, count in world.market.requests if label == "15m"]
    assert short_requests[0] - short_requests[1] == 10


def test_the_indicators_read_as_a_cycle_of_the_interval_of_a_flow_that_names_none() -> None:
    default, hourly = World(), World(CycleInterval(60))

    default.trial.execute(TrySourceAdapterCommand("indicatori", "Hyperliquid", "BTC"))
    hourly.trial.execute(TrySourceAdapterCommand("indicatori", "Hyperliquid", "BTC"))

    assert [label for _, label, _ in default.market.requests] == ["15m", "4h"]
    assert [label for _, label, _ in hourly.market.requests] == ["1h", "4h"]


def test_the_trial_waits_for_the_source_as_the_cycles_do() -> None:
    world = World()

    world.trial.execute(TrySourceAdapterCommand("notizie", "RSS"))

    assert world.calls.waits == [60.0]


def test_a_source_that_does_not_answer_in_time_is_a_transient_error() -> None:
    world = World()
    world.calls.silent = True

    trial = world.trial.execute(TrySourceAdapterCommand("notizie", "RSS"))

    assert (trial.outcome, trial.reason, trial.permanent) == (
        TrialOutcome.FAILED,
        "nessuna risposta entro 60 secondi",
        False,
    )
    assert trial.response_milliseconds == 250


def test_a_source_that_fails_is_the_outcome_with_its_reason_and_its_permanence() -> None:
    world = World()
    world.news.reachable = False

    trial = world.trial.execute(TrySourceAdapterCommand("notizie", "RSS"))

    assert (trial.outcome, trial.values, trial.reason, trial.permanent) == (
        TrialOutcome.FAILED,
        (),
        "fonte non raggiungibile: notizie",
        False,
    )


def test_a_source_of_the_market_is_read_once_for_the_whole_market() -> None:
    world = World()

    trial = world.trial.execute(TrySourceAdapterCommand("sentiment", "alternative.me", "BTC"))

    assert [value.values["valore"] for value in trial.values] == ["50"]
    assert world.market.requests == []


def test_an_adapter_that_needs_configuration_reads_with_the_credentials_of_the_tenant() -> None:
    world = World()
    world.configure_paid()

    trial = world.trial.execute(TrySourceAdapterCommand("sentiment", PAID))

    assert world.paid.received == [{"api_key": "K-PAID"}]
    assert [value.values["valore"] for value in trial.values] == ["40"]


def test_an_adapter_not_configured_fails_with_the_reason_without_being_read() -> None:
    world = World()

    trial = world.trial.execute(TrySourceAdapterCommand("sentiment", PAID))

    assert (trial.outcome, trial.reason) == (TrialOutcome.FAILED, NOT_CONFIGURED)
    assert world.paid.received == []


def test_credentials_refused_by_the_provider_fail_the_trial_without_marking_them() -> None:
    world = World()
    world.configure_paid()
    world.paid.rejects_credentials = True

    trial = world.trial.execute(TrySourceAdapterCommand("sentiment", PAID))

    saved = world.credentials.get(PAID)
    assert (trial.outcome, trial.reason) == (TrialOutcome.FAILED, "credenziali rifiutate dal fornitore: Pagato")
    assert saved is not None
    assert saved.rejected_at is None


def test_the_forecast_of_a_trial_is_never_recorded() -> None:
    world = World()

    trial = world.trial.execute(TrySourceAdapterCommand("forecast", "Prophet", "BTC"))

    assert trial.outcome is TrialOutcome.SUCCEEDED
    assert world.forecasts.forecasts == []


@pytest.mark.parametrize(
    ("command", "refusal"),
    [
        (TrySourceAdapterCommand("meteo", "Hyperliquid", "BTC"), SourceNotAvailableError),
        (TrySourceAdapterCommand("indicatori", "altro", "BTC"), SourceAdapterNotAvailableError),
        (
            TrySourceAdapterCommand("indicatori", "Hyperliquid", "BTC", {"lunghezza_serie": 51}),
            SourceParameterOutOfRangeError,
        ),
        (TrySourceAdapterCommand("indicatori", "Hyperliquid"), TrialAssetRequiredError),
    ],
    ids=["unknown-source", "unknown-adapter", "parameter-out-of-range", "missing-asset"],
)
def test_a_request_that_cannot_be_read_is_refused_before_reading(
    command: TrySourceAdapterCommand, refusal: type[Exception]
) -> None:
    world = World()

    with pytest.raises(refusal):
        world.trial.execute(command)

    assert (world.market.requests, world.calls.waits) == ([], [])
