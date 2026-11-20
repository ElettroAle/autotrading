"""R5.1.1: the large transfers of the last interval of the flow, above the threshold of the adapter, enter the context
of the cycle; without them the context says so, and a provider that does not answer is an absent source. On the cycle
the worker composes, with the fake adapters (ADR fonte-whale-con-adapter-arkham).
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, AdapterSelection, SourceSelection
from autotrading.domain.sources.whale_transfer import WhaleTransfer
from tests.fakes.whale_transfers import API_KEY, FakeWhaleTransfersAdapter
from tests.support.flow_cycles import FlowCycles, at
from tests.support.source_keys import configure_paid
from tests.support.steps import quoted

scenarios("E5-evoluzioni/F5.1-nuove-fonti/R5.1.1-grandi-trasferimenti.feature")

USER = "anna"
WHALE = "whale"
TYPED_KEY = "K-ARKHAM-SEGRETA"
EXCHANGE = "Binance (Hot Wallet)"
DEFAULT_THRESHOLD = 1_000_000


@dataclass
class WhaleCycles:
    """The cycles of the flow of anna, with the provider of the large transfers the platform offers."""

    cycles: FlowCycles = field(default_factory=FlowCycles)
    flow: str = ""
    provider: FakeWhaleTransfersAdapter | None = None

    def adapter(self) -> FakeWhaleTransfersAdapter:
        assert self.provider is not None
        return self.provider

    def whale_entries(self) -> list[dict[str, str]]:
        return self.cycles.sources_in_context(WHALE)


@pytest.fixture
def whales() -> WhaleCycles:
    return WhaleCycles()


def selected(adapter: str, minutes: int) -> Callable[[FlowConfiguration], FlowConfiguration]:
    def change(configuration: FlowConfiguration) -> FlowConfiguration:
        selection = SourceSelection(WHALE, (AdapterSelection(adapter, DEFAULT_WEIGHT, {}),))
        return replace(configuration, cycle_interval=CycleInterval(minutes), sources=(selection,))

    return change


# Given


@given(
    quoted(
        'che il flusso "{flow}" ha intervallo {minutes} minuti e la fonte "{source}" con l\'adapter "{adapter}" '
        "configurato"
    )
)
def flow_with_whale_source(whales: WhaleCycles, flow: str, minutes: str, source: str, adapter: str) -> None:
    assert source == WHALE
    cycles = whales.cycles
    whales.provider = FakeWhaleTransfersAdapter(adapter)
    cycles.whales[adapter] = whales.provider
    cycles.platform.source_systems = cycles.systems()
    cycles.add_flow(USER, flow)
    configure_paid(cycles, USER, adapter, TYPED_KEY)
    cycles.reconfigure(flow, selected(adapter, int(minutes)))
    whales.flow = flow


@given("che nell'ultima ora c'è stato un trasferimento di 500 BTC da un wallet a un exchange")
def large_transfer_last_hour(whales: WhaleCycles) -> None:
    whales.adapter().published = [
        WhaleTransfer(at("09:40"), "BTC", Decimal(500), Decimal("45000000"), None, EXCHANGE),
        # Before the last interval: it stays out of the context.
        WhaleTransfer(at("08:30"), "BTC", Decimal(800), Decimal("72000000"), None, EXCHANGE),
    ]


@given("che nell'ultima ora ci sono stati solo trasferimenti sotto 1.000.000 USD")
def only_small_transfers(whales: WhaleCycles) -> None:
    whales.adapter().published = [
        WhaleTransfer(at("09:20"), "ETH", Decimal(250), Decimal("999999"), "Coinbase", None),
        WhaleTransfer(at("09:50"), "BTC", Decimal(5), Decimal("450000"), None, EXCHANGE),
    ]


@given("che Arkham non risponde")
def provider_unreachable(whales: WhaleCycles) -> None:
    whales.adapter().reachable = False


# When


@when(quoted('parte il ciclo di "{flow}"'))
def cycle_starts(whales: WhaleCycles, flow: str) -> None:
    whales.cycles.run(flow)


# Then


@then("il contesto contiene il trasferimento con data e ora, asset, quantità, controvalore e descrizione")
def transfer_in_context(whales: WhaleCycles) -> None:
    assert whales.whale_entries() == [
        {
            "data_ora": "2026-11-12T09:40:00+00:00",
            "asset": "BTC",
            "quantita": "500",
            "controvalore_usd": "45000000",
            "descrizione": f"da indirizzo non etichettato a {EXCHANGE}",
        }
    ]
    # The window is the last interval of the flow, the threshold the default of the adapter, with the key of anna.
    [asked] = whales.adapter().asked
    now = at("10:00")
    assert (asked.since, asked.until, asked.minimum_usd) == (now - timedelta(minutes=60), now, DEFAULT_THRESHOLD)
    assert asked.credentials == {API_KEY.name: TYPED_KEY}


@then(quoted('il contesto dice "{note}"'))
def context_says(whales: WhaleCycles, note: str) -> None:
    assert whales.whale_entries() == [{"nota": note}]
    assert whales.cycles.last_record(whales.flow).absent_sources == ()


@then(quoted('la fonte "{source}" è assente nel contesto e il ciclo prosegue'))
def absent_and_cycle_goes_on(whales: WhaleCycles, source: str) -> None:
    record = whales.cycles.last_record(whales.flow)
    [absent] = record.absent_sources
    assert (absent.source, absent.adapter) == (source, whales.adapter().name)
    assert whales.cycles.context()["dati_mancanti"] == [f"{absent.label}: {absent.reason}"]
    assert whales.whale_entries() == []
    assert CycleStep.AGENT_DECISION in record.steps
    assert record.outcome is CycleOutcome.COMPLETED
