"""R5.1.2: the volume of the last 24 hours, the ratio of the aggressive buys to the aggressive sells over the interval
of the cycle and the imbalance of the order book within 1% of the price, of every asset of the flow on another
exchange, enter the context of the cycle; an asset the exchange does not list is declared, and an exchange that does
not answer is an absent source. On the cycle the worker composes, with the fake adapters (ADR
fonte-volumi-con-adapter-binance).
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, AdapterSelection, SourceSelection
from autotrading.domain.sources.volume_snapshot import BookLevel, VolumeSnapshot
from tests.fakes.volumes import FakeVolumesAdapter, VolumesAsked
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios("E5-evoluzioni/F5.1-nuove-fonti/R5.1.2-volumi-e-order-book/worker/R5.1.2-volumi-e-order-book.feature")

USER = "anna"
VOLUMES = "volumi"
UNLISTED = "PURR"
CYCLE_MINUTES = 15
# Bids at 99500 and asks at 100500 put the mid price at 100000: the levels at 98000 and 102000 are beyond 1%.
SNAPSHOT = VolumeSnapshot(
    Decimal("1500000000.4"),
    Decimal(6_000_000),
    Decimal(4_000_000),
    (BookLevel(Decimal(99500), Decimal(10)), BookLevel(Decimal(98000), Decimal(5))),
    (BookLevel(Decimal(100500), Decimal(6)), BookLevel(Decimal(102000), Decimal(50))),
)


@dataclass
class VolumeCycles:
    """The cycles of the flow of anna, with the exchange of the volumes the platform offers."""

    cycles: FlowCycles = field(default_factory=FlowCycles)
    flow: str = ""
    exchange: FakeVolumesAdapter | None = None

    def adapter(self) -> FakeVolumesAdapter:
        assert self.exchange is not None
        return self.exchange

    def volume_entries(self, asset: str) -> list[dict[str, str]]:
        return self.cycles.sources_in_context(VOLUMES, asset)


@pytest.fixture
def volumes() -> VolumeCycles:
    return VolumeCycles()


def selected(adapter: str) -> Callable[[FlowConfiguration], FlowConfiguration]:
    def change(configuration: FlowConfiguration) -> FlowConfiguration:
        selection = SourceSelection(VOLUMES, (AdapterSelection(adapter, DEFAULT_WEIGHT, {}),))
        return replace(configuration, sources=(selection,))

    return change


def with_asset(asset: str) -> Callable[[FlowConfiguration], FlowConfiguration]:
    def change(configuration: FlowConfiguration) -> FlowConfiguration:
        return replace(configuration, assets=(*configuration.assets, asset))

    return change


# Given


@given(quoted('che il flusso "{flow}" ha l\'asset "{asset}" e la fonte "{source}" con l\'adapter "{adapter}"'))
def flow_with_volumes_source(volumes: VolumeCycles, flow: str, asset: str, source: str, adapter: str) -> None:
    assert source == VOLUMES
    cycles = volumes.cycles
    volumes.exchange = FakeVolumesAdapter(adapter, published={asset: SNAPSHOT})
    cycles.volumes[adapter] = volumes.exchange
    cycles.platform.source_systems = cycles.systems()
    cycles.add_flow(USER, flow, assets=(asset,))
    cycles.reconfigure(flow, selected(adapter))
    volumes.flow = flow


@given(quoted('che il flusso "{flow}" ha anche un asset non quotato su {adapter}'))
def flow_with_unlisted_asset(volumes: VolumeCycles, flow: str, adapter: str) -> None:
    assert adapter == volumes.adapter().name
    volumes.cycles.reconfigure(flow, with_asset(UNLISTED))


@given(quoted("che {adapter} non risponde"))
def exchange_unreachable(volumes: VolumeCycles, adapter: str) -> None:
    assert adapter == volumes.adapter().name
    volumes.adapter().reachable = False


# When


@when(quoted('parte il ciclo di "{flow}"'))
def cycle_starts(volumes: VolumeCycles, flow: str) -> None:
    volumes.cycles.run(flow)


# Then


@then(
    quoted(
        'il contesto contiene per "{asset}" su {adapter} volume 24 ore, rapporto taker buy/sell e squilibrio '
        "dell'order book entro ±1%"
    )
)
def volumes_in_context(volumes: VolumeCycles, asset: str, adapter: str) -> None:
    entries = volumes.cycles.context()["fonti"]
    assert isinstance(entries, list)
    assert [entry["adapter"] for entry in entries if entry["fonte"] == VOLUMES and entry["asset"] == asset] == [adapter]
    # 995000 of bids against 603000 of asks within 1% of the mid price.
    assert volumes.volume_entries(asset) == [
        {
            "volume_24h_usd": "1500000000",
            "rapporto_taker_buy_sell": "1.5000",
            "squilibrio_order_book_1_percento": "0.6227",
        }
    ]
    # The aggressive trades are those of the interval of the cycle of the flow.
    assert volumes.adapter().asked == [VolumesAsked(asset, CYCLE_MINUTES)]


@then(quoted('il contesto dice per quell\'asset "{note}"'))
def unlisted_in_context(volumes: VolumeCycles, note: str) -> None:
    assert volumes.volume_entries(UNLISTED) == [{"nota": note}]
    assert volumes.cycles.last_record(volumes.flow).absent_sources == ()


@then(quoted('la fonte "{source}" è assente nel contesto e il ciclo prosegue'))
def absent_and_cycle_goes_on(volumes: VolumeCycles, source: str) -> None:
    record = volumes.cycles.last_record(volumes.flow)
    [absent] = record.absent_sources
    assert (absent.source, absent.adapter) == (source, volumes.adapter().name)
    assert volumes.cycles.context()["dati_mancanti"] == [f"{absent.label}: {absent.reason}"]
    assert volumes.cycles.sources_in_context(VOLUMES) == []
    assert CycleStep.AGENT_DECISION in record.steps
    assert record.outcome is CycleOutcome.COMPLETED
