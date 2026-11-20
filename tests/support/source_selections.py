"""The sources of a flow as the tests choose them: a source with the adapter that offers it on the platform (R4.1.1)."""

from collections.abc import Mapping

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.ports import AdapterRequest
from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, AdapterSelection, SourceSelection
from autotrading.domain.sources.source_catalog import SourceCatalog
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter

# The adapter every source of the platform has today, by the name its declaration gives; the sentiment has two.
ADAPTER_OF = {
    "indicatori": "Hyperliquid",
    "pivot": "Hyperliquid",
    "forecast": "Prophet",
    "sentiment": "alternative.me",
    "notizie": "RSS",
}
# The sources of the flows before the adapters: each one is now a source with one of its adapters (ADR
# migrazione-delle-fonti-al-modello-ad-adapter).
BEFORE_THE_ADAPTERS = {
    "sentiment-alternative-me": ("sentiment", "alternative.me"),
    "sentiment-coinmarketcap": ("sentiment", "CoinMarketCap"),
}


def adapter_of(source: str) -> str:
    """The adapter a test activates for the source: the one the platform offers, or the source itself when unknown."""
    return ADAPTER_OF.get(source, source)


def reader_of(name: str) -> tuple[str, str]:
    """The source and its adapter a name of the specifications means, the names before the adapters included."""
    return BEFORE_THE_ADAPTERS.get(name, (name, adapter_of(name)))


def a_source(
    name: str,
    weight: int = DEFAULT_WEIGHT,
    parameters: Mapping[str, int] | None = None,
    adapter: str | None = None,
) -> SourceSelection:
    """A source of the flow with one adapter, its weight and its parameters."""
    chosen = adapter_of(name) if adapter is None else adapter
    return SourceSelection(name, (AdapterSelection(chosen, weight, dict(parameters or {})),))


def platform_systems() -> SourceSystems:
    """The adapters of the sources of the platform of E1, fakes declaring the names of the real ones: no provider of the
    large transfers nor exchange of the volumes, which a test offers when it needs one (R5.1.1, R5.1.2)."""
    return SourceSystems(
        (FakeSentimentAdapter("alternative.me"), FakeSentimentAdapter("CoinMarketCap")),
        FakeNewsAdapter(),
        FakePriceHistoryAdapter(),
        FakePriceForecasterAdapter(),
        FakeMarketDataAdapter(),
        (),
        (),
    )


def platform_sources() -> ListSourcesUseCase:
    return ListSourcesUseCase(platform_systems())


# The catalog of the platform: every source with the adapters that offer it (R4.1.1).
PLATFORM_CATALOG: SourceCatalog = platform_sources().execute()


def a_source_request(
    name: str, weight: int | None = None, parameters: Mapping[str, int] | None = None, adapter: str | None = None
) -> SourceRequest:
    """A source the user asks for with one adapter; a name before the adapters asks for the adapter it became."""
    source, chosen = reader_of(name) if adapter is None else (name, adapter)
    return SourceRequest(source, (AdapterRequest(chosen, weight, dict(parameters or {})),))
