"""Closings that enter the history of a flow, from a cycle or from outside the platform (R1.7.2, ADR 0056, 0070)."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.record_flow_closing import RecordFlowClosingCommand, RecordFlowClosingUseCase
from autotrading.application.flows.record_outside_closing import (
    RecordOutsideClosingCommand,
    RecordOutsideClosingUseCase,
)
from autotrading.domain.flows.account_reconciliation import OutsideClosing
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

TENANT = TenantId(uuid4())
OPENED = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)
CLOSED = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
CYCLE = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
OPENING = PositionOpening(TradeSide.LONG, 2, Decimal(50), PositionEnd(Decimal(100000), OPENED, OPENED), Decimal("0.03"))


class KnownOpenings:
    def __init__(self) -> None:
        self.openings: dict[tuple[FlowId, str], PositionOpening] = {}

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        return self.openings.get((flow_id, asset))


class ToldClosings:
    def __init__(self) -> None:
        self.told: list[tuple[str, str, Decimal]] = []

    def tell(self, flow: Flow, asset: str, realized_pnl: Decimal) -> None:
        self.told.append((flow.name.value, asset, realized_pnl))


class Bench:
    def __init__(self) -> None:
        self.flows = FlowStore()
        self.history = ClosedPositionStore()
        self.openings = KnownOpenings()
        self.notices = ToldClosings()
        self.flow = a_flow(TENANT)
        self.flows.flows.append(self.flow)
        closed_positions = InMemoryClosedPositionRepositoryAdapter(self.history, TENANT)
        self.cycle_closing = RecordFlowClosingUseCase(self.openings, closed_positions, self.notices)
        self.outside_closing = RecordOutsideClosingUseCase(
            InMemoryFlowRepositoryAdapter(self.flows, TENANT), self.openings, closed_positions, self.notices
        )

    def close_in_cycle(self) -> None:
        command = RecordFlowClosingCommand(
            self.flow, "BTC", Decimal(102000), CLOSED, Decimal("0.05"), Decimal("1.5"), CYCLE
        )
        self.cycle_closing.execute(command)

    def close_outside(self, realized_pnl: Decimal = Decimal("2")) -> OutsideClosing:
        closing = OutsideClosing(self.flow.id, "BTC", realized_pnl, Decimal("0.04"), CLOSED)
        self.outside_closing.execute(RecordOutsideClosingCommand(closing))
        return closing


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_a_cycle_closing_enters_the_history_with_the_agent_reason_and_its_cycle(bench: Bench) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    bench.close_in_cycle()

    fill = ClosingFill(Decimal(102000), CLOSED, Decimal("0.05"), Decimal("1.5"))
    assert bench.history.positions == [OPENING.closed(bench.flow, "BTC", fill, CloseReason.AGENT, cycle=CYCLE)]
    assert bench.notices.told == []


def test_a_cycle_closing_the_flow_never_opened_is_told_on_its_own(bench: Bench) -> None:
    bench.close_in_cycle()

    assert bench.history.positions == []
    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal("1.5"))]


def test_a_position_closed_outside_enters_the_history_of_the_flow(bench: Bench) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    closing = bench.close_outside()

    assert bench.history.positions == [OPENING.closed_outside(bench.flow, closing)]
    assert bench.notices.told == []


def test_a_position_closed_outside_the_flow_never_opened_is_told_and_logged(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.close_outside()

    assert bench.history.positions == []
    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal("2"))]
    (record,) = caplog.records
    assert record.getMessage() == "posizione chiusa fuori senza apertura del flusso"
    assert (record.__dict__["flow_id"], record.__dict__["asset"]) == (str(bench.flow.id.value), "BTC")


def test_a_loss_beyond_the_value_of_the_position_is_told_and_logged(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.close_outside(Decimal(-150))

    assert bench.history.positions == []
    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal(-150))]
    (record,) = caplog.records
    assert record.getMessage() == "esito della chiusura fuori non rappresentabile"
