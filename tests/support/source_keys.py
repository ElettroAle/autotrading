"""The page of the keys of one tenant on the fake adapters, with a paid adapter of the sentiment (R4.1.2)."""

from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import uuid4

from autotrading.application.sources.configure_source_adapter import (
    ConfigureSourceAdapterCommand,
    ConfigureSourceAdapterUseCase,
)
from autotrading.application.sources.list_source_credentials import ListSourceCredentialsUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, AdapterSelection, SourceSelection
from autotrading.domain.sources.source_adapter_declaration import SourceConfigurationField
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.source_credentials import (
    FakeSourceSecretsSealerAdapter,
    InMemorySourceCredentialsRepositoryAdapter,
    SourceCredentialsStore,
    SourceSecretsVault,
)
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter
from tests.support.flow_cycles import FlowCycles

PAID = "Pagato"
SENTIMENT = "sentiment"
API_KEY = SourceConfigurationField("api_key", "Chiave API", secret=True)
ACCOUNT = SourceConfigurationField("account", "Account", secret=False)
TODAY = datetime(2026, 11, 15, 6, 0, tzinfo=UTC)
REJECTED_AT = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)


class Keys:
    """The page of the keys of one tenant on the fake adapters, with a paid adapter of the sentiment."""

    def __init__(self, tenant_id: TenantId | None = None, store: SourceCredentialsStore | None = None) -> None:
        self.tenant_id = TenantId(uuid4()) if tenant_id is None else tenant_id
        self.store = SourceCredentialsStore() if store is None else store
        self.vault: SourceSecretsVault = {}
        self.sources = ListSourcesUseCase(
            SourceSystems(
                (FakeSentimentAdapter("libero"), FakeSentimentAdapter(PAID, configuration_fields=(API_KEY, ACCOUNT))),
                FakeNewsAdapter(),
                FakePriceHistoryAdapter(),
                FakePriceForecasterAdapter(),
                FakeMarketDataAdapter(),
                (),
            )
        )
        self.credentials = InMemorySourceCredentialsRepositoryAdapter(self.store, self.tenant_id)
        self.sealer = FakeSourceSecretsSealerAdapter(self.tenant_id, self.vault)
        self.configure = ConfigureSourceAdapterUseCase(self.tenant_id, self.sources, self.credentials, self.sealer)
        self.listing = ListSourceCredentialsUseCase(self.sources, self.credentials, lambda: TODAY)

    def configure_paid(self, key: str = "K-PAID", expires_on: date | None = None) -> None:
        self.configure.execute(ConfigureSourceAdapterCommand(PAID, {"api_key": key, "account": "anna"}, expires_on))


def offer_paid_sentiment(flow_cycles: FlowCycles, adapter: str) -> FakeSentimentAdapter:
    """A paid adapter of the sentiment beside those of the platform, in the API and in the worker, that asks for a
    secret API key (R4.1.2)."""
    paid = FakeSentimentAdapter(adapter, configuration_fields=(API_KEY,))
    flow_cycles.sentiments[adapter] = paid
    flow_cycles.platform.source_systems = flow_cycles.systems()
    return paid


def configure_paid(flow_cycles: FlowCycles, user: str, adapter: str, key: str = "K-LUNAR") -> None:
    command = ConfigureSourceAdapterCommand(adapter, {API_KEY.name: key})
    flow_cycles.platform.use_cases_of(user).configure_source_adapter.execute(command)


def use_paid_sentiment(flow_cycles: FlowCycles, flow: str, adapter: str) -> None:
    """The flow reads the sentiment from the paid adapter alone, with the defaults of the catalog."""
    settings = ListSourcesUseCase(flow_cycles.systems()).execute().find(SENTIMENT).settings(adapter, {})
    selection = SourceSelection(SENTIMENT, (AdapterSelection(adapter, DEFAULT_WEIGHT, settings),))
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, sources=(selection,)))
