from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.ports import FlowSnapshot, SourceAsk, SourceRequest
from autotrading.application.flows.read_cycle_source import ReadCycleSourceUseCase
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.errors import SourceNotSelectedError
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.cycles import FakeClockAdapter
from tests.support.flows import a_configuration, a_flow

PLANNED_AT = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
NOW = PLANNED_AT + timedelta(seconds=2)
TENANT = TenantId.new()
CONFIGURATION = replace(
    a_configuration(assets=("BTC", "ETH")), sources=(SourceSelection("indicatori", 8, {"periodo_rsi": 21}),)
)
FLOW = a_flow(TENANT, configuration=CONFIGURATION)
STATE = FlowState(FLOW.id, "USDC", Decimal(500), (), Decimal(0), Decimal(0), Decimal(0))
CYCLE_FLOW = CycleFlow(TENANT, FLOW, "test-1", "Hyperliquid", PLANNED_AT, CycleAccount("USDC", Decimal(500), ()), STATE)
REQUEST = SourceRequest(FLOW.id.value, PLANNED_AT, FlowSnapshot(("indicatori",), CYCLE_FLOW))


@dataclass(frozen=True, slots=True)
class Collected:
    source: str
    weight: int
    entries: tuple[tuple[str | None, dict[str, str]], ...]


class RecordedCollectionAdapter:
    def __init__(self, entries: tuple[tuple[str | None, dict[str, str]], ...]) -> None:
        self.entries = entries
        self.asks: list[SourceAsk] = []

    def execute(self, ask: SourceAsk) -> Collected:
        self.asks.append(ask)
        return Collected(ask.source, ask.weight, self.entries)


def test_the_source_is_asked_with_the_parameters_assets_and_interval_of_the_flow() -> None:
    collection = RecordedCollectionAdapter(())

    ReadCycleSourceUseCase(collection, FakeClockAdapter(NOW)).execute(REQUEST, "indicatori")

    assert collection.asks == [
        SourceAsk(
            FLOW.id.value,
            PLANNED_AT,
            "indicatori",
            8,
            {"periodo_rsi": 21},
            ("BTC", "ETH"),
            CONFIGURATION.cycle_interval.minutes,
            NOW,
        )
    ]


def test_every_collected_value_reaches_the_cycle_with_the_weight_of_its_source() -> None:
    collection = RecordedCollectionAdapter((("BTC", {"rsi": "55"}), (None, {"nota": "mercato chiuso"})))

    data = ReadCycleSourceUseCase(collection, FakeClockAdapter(NOW)).execute(REQUEST, "indicatori")

    assert data == (
        SourceData("indicatori", 8, "BTC", {"rsi": "55"}),
        SourceData("indicatori", 8, None, {"nota": "mercato chiuso"}),
    )


def test_a_source_the_flow_does_not_select_is_refused() -> None:
    with pytest.raises(SourceNotSelectedError):
        ReadCycleSourceUseCase(RecordedCollectionAdapter(()), FakeClockAdapter(NOW)).execute(REQUEST, "notizie")
