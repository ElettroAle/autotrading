import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.record_manual_closing import (
    RecordManualClosingCommand,
    RecordManualClosingUseCase,
)
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
OPENED = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)
FILL = ClosingFill(Decimal(102000), datetime(2026, 11, 12, 9, 45, tzinfo=UTC), Decimal("0.05"))
OPENING = PositionOpening(TradeSide.LONG, 2, Decimal(50), PositionEnd(Decimal(100000), OPENED, OPENED), Decimal("0.03"))


class KnownOpenings:
    """The last opening of each flow on each asset, as the orders the platform recorded give it."""

    def __init__(self) -> None:
        self.openings: dict[tuple[FlowId, str], PositionOpening] = {}

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        return self.openings.get((flow_id, asset))


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.history = ClosedPositionStore()
        self.openings = KnownOpenings()
        self.use_case = RecordManualClosingUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT),
            self.openings,
            InMemoryClosedPositionRepositoryAdapter(self.history, TENANT),
        )

    def flow(
        self, assets: tuple[str, ...] = ("BTC",), status: FlowStatus = FlowStatus.ACTIVE, account: UUID = ACCOUNT
    ) -> Flow:
        flow = a_flow(TENANT, status=status, account_id=account, configuration=a_configuration(assets=assets))
        self.store.flows.append(flow)
        return flow

    def record(self, asset: str = "BTC", account: UUID = ACCOUNT) -> None:
        self.use_case.execute(RecordManualClosingCommand(account, asset, FILL))


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_a_position_of_a_flow_closed_by_hand_enters_its_history_with_the_manual_reason(bench: Bench) -> None:
    flow = bench.flow(("ETH", "BTC"))
    bench.openings.openings[flow.id, "BTC"] = OPENING

    bench.record()

    assert bench.history.positions == [OPENING.closed(flow, "BTC", FILL, CloseReason.MANUAL)]


@pytest.mark.parametrize("status", [FlowStatus.ACTIVE, FlowStatus.PAUSED, FlowStatus.STOPPED])
def test_the_flow_that_owns_the_asset_on_the_account_takes_the_closing(bench: Bench, status: FlowStatus) -> None:
    bench.flow(("ETH",))
    bench.flow(("BTC",), account=uuid4())
    owner = bench.flow(("BTC",), status=status)
    bench.openings.openings[owner.id, "BTC"] = OPENING

    bench.record()

    assert [position.flow_id for position in bench.history.positions] == [owner.id]


def test_an_archived_flow_does_not_take_the_closing(bench: Bench) -> None:
    archived = bench.flow(status=FlowStatus.ARCHIVED)
    bench.openings.openings[archived.id, "BTC"] = OPENING

    bench.record()

    assert bench.history.positions == []


def test_an_asset_no_flow_trades_on_the_account_has_no_history(bench: Bench) -> None:
    flow = bench.flow(("ETH",))
    bench.openings.openings[flow.id, "BTC"] = OPENING

    bench.record()

    assert bench.history.positions == []


def test_a_position_the_flow_never_opened_has_no_history(bench: Bench, caplog: pytest.LogCaptureFixture) -> None:
    flow = bench.flow()

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.record()

    assert bench.history.positions == []
    (record,) = caplog.records
    assert record.getMessage() == "posizione chiusa a mano senza apertura del flusso"
    assert (record.__dict__["flow_id"], record.__dict__["asset"]) == (str(flow.id.value), "BTC")
