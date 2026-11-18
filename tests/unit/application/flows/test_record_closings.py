"""Closings that enter the history of a flow and are told, from a cycle, from outside the platform or by a protection on
the exchange (R1.7.2, R3.1.2, ADR 0056, 0070, ADR chiusure-per-protezione-nello-storico)."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.ports import ProtectedPosition
from autotrading.application.flows.record_flow_closing import RecordFlowClosingUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.flows.record_protection_closing import RecordProtectionClosingUseCase
from autotrading.domain.flows.account_reconciliation import OutsideClosing, ProtectionClosing
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionOpening
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.position_closed_notices import FakePositionClosedNoticeAdapter
from tests.fakes.protection_cancellation import FakeProtectionCancellationAdapter
from tests.support.flows import a_flow

TENANT = TenantId(uuid4())
OPENED = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)
CLOSED = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
CYCLE = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
PLAN = ExitPlan(Decimal(110000), Decimal(95000), "chiusura sotto 97000")
OPENING = PositionOpening(TradeSide.LONG, 2, Decimal(50), PositionEnd(Decimal(100000), OPENED, OPENED), Decimal("0.03"))


class KnownOpenings:
    def __init__(self) -> None:
        self.openings: dict[tuple[FlowId, str], PositionOpening] = {}

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        return self.openings.get((flow_id, asset))


@dataclass(frozen=True, slots=True)
class Executed:
    average_price: Decimal
    executed_at: datetime
    fee: Decimal
    realized_pnl: Decimal


class Bench:
    def __init__(self) -> None:
        self.flows = FlowStore()
        self.history = ClosedPositionStore()
        self.openings = KnownOpenings()
        self.notices = FakePositionClosedNoticeAdapter()
        self.flow = a_flow(TENANT)
        self.flows.flows.append(self.flow)
        closed_positions = InMemoryClosedPositionRepositoryAdapter(self.history, TENANT)
        flows = InMemoryFlowRepositoryAdapter(self.flows, TENANT)
        self.exit_plans = InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), TENANT)
        self.exit_plans.save(self.flow.id, "BTC", PLAN)
        self.cycle_closing = RecordFlowClosingUseCase(
            flows, self.openings, closed_positions, self.notices, self.exit_plans
        )
        self.cancellation = FakeProtectionCancellationAdapter()
        self.outside_closing = RecordOutsideClosingUseCase(
            flows, self.openings, closed_positions, self.notices, self.exit_plans, self.cancellation
        )
        self.protection_closing = RecordProtectionClosingUseCase(
            flows, self.openings, closed_positions, self.notices, self.exit_plans, self.cancellation
        )

    def close_in_cycle(self) -> None:
        fill = Executed(Decimal(102000), CLOSED, Decimal("0.05"), Decimal("1.5"))
        self.cycle_closing.execute(self.flow.id.value, CYCLE, "BTC", fill)

    def close_by_protection(
        self, reason: CloseReason = CloseReason.STOP_LOSS, realized_pnl: Decimal = Decimal("-5.1")
    ) -> ProtectionClosing:
        closing = ProtectionClosing(self.flow.id, "BTC", reason, realized_pnl, Decimal("0.04"), CLOSED)
        self.protection_closing.execute(closing)
        return closing

    def close_outside(self, realized_pnl: Decimal = Decimal("2"), *, liquidation: bool = False) -> OutsideClosing:
        closing = OutsideClosing(self.flow.id, "BTC", realized_pnl, Decimal("0.04"), CLOSED, liquidation)
        self.outside_closing.execute(closing)
        return closing


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_a_cycle_closing_enters_the_history_with_the_agent_reason_and_its_cycle_then_is_told(bench: Bench) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    bench.close_in_cycle()

    fill = ClosingFill(Decimal(102000), CLOSED, Decimal("0.05"), Decimal("1.5"))
    position = OPENING.closed(bench.flow, "BTC", fill, CloseReason.AGENT, cycle=CYCLE)
    assert bench.history.positions == [position]
    assert bench.notices.told == [(bench.flow.name.value, "BTC", position.pnl, "decisione dell'agente")]


def test_a_cycle_closing_the_flow_never_opened_is_told_on_its_own(bench: Bench) -> None:
    bench.close_in_cycle()

    assert bench.history.positions == []
    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal("1.5"), "decisione dell'agente")]


def test_a_position_closed_outside_enters_the_history_of_the_flow_then_is_told(bench: Bench) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    closing = bench.close_outside()

    position = OPENING.closed_outside(bench.flow, closing)
    assert bench.history.positions == [position]
    assert bench.notices.told == [(bench.flow.name.value, "BTC", position.pnl, "chiusa fuori dalla piattaforma")]


@pytest.mark.parametrize("opened", [True, False])
def test_a_position_liquidated_is_told_as_a_liquidation_and_kept_as_a_closing_outside(
    bench: Bench, *, opened: bool
) -> None:
    if opened:
        bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    bench.close_outside(Decimal(-48), liquidation=True)

    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal(-48), "liquidazione")]
    assert [position.reason for position in bench.history.positions] == [CloseReason.OUTSIDE_PLATFORM] * opened


def test_a_position_closed_outside_the_flow_never_opened_is_told_and_logged(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.close_outside()

    assert bench.history.positions == []
    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal("2"), "chiusa fuori dalla piattaforma")]
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
    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal(-150), "chiusa fuori dalla piattaforma")]
    (record,) = caplog.records
    assert record.getMessage() == "esito della chiusura fuori non rappresentabile"


@pytest.mark.parametrize("opened", [True, False])
def test_a_cycle_closing_ends_the_exit_plan_of_the_position(bench: Bench, *, opened: bool) -> None:
    if opened:
        bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    bench.close_in_cycle()

    assert bench.exit_plans.current(bench.flow.id, "BTC") is None


@pytest.mark.parametrize("opened", [True, False])
def test_a_closing_outside_ends_the_exit_plan_of_the_position(bench: Bench, *, opened: bool) -> None:
    if opened:
        bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    bench.close_outside()

    assert bench.exit_plans.current(bench.flow.id, "BTC") is None


def test_a_closing_outside_beyond_the_value_of_the_position_still_ends_its_plan(bench: Bench) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    bench.close_outside(Decimal(-150))

    assert bench.exit_plans.current(bench.flow.id, "BTC") is None


def test_a_cycle_closing_after_a_refused_stop_loss_enters_the_history_with_that_reason(bench: Bench) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING
    fill = Executed(Decimal(102000), CLOSED, Decimal("0.05"), Decimal("1.5"))

    bench.cycle_closing.execute(bench.flow.id.value, CYCLE, "BTC", fill, unprotected=True)

    [position] = bench.history.positions
    assert position.reason is CloseReason.PROTECTION_MISSING


def test_a_cycle_closing_that_reverses_the_position_enters_the_history_as_a_reversal(bench: Bench) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING
    fill = Executed(Decimal(102000), CLOSED, Decimal("0.05"), Decimal("1.5"))

    bench.cycle_closing.execute(bench.flow.id.value, CYCLE, "BTC", fill, reversing=True)

    [position] = bench.history.positions
    assert position.reason is CloseReason.REVERSAL
    assert bench.exit_plans.current(bench.flow.id, "BTC") is None


def test_a_closing_outside_cancels_the_protections_left_on_the_exchange(bench: Bench) -> None:
    bench.close_outside()

    assert bench.cancellation.cancelled == [ProtectedPosition(bench.flow.assigned_account_id, "BTC")]


@pytest.mark.parametrize("reason", [CloseReason.STOP_LOSS, CloseReason.TAKE_PROFIT])
def test_a_closing_by_protection_enters_the_history_with_its_reason_and_the_outcome_of_the_exchange(
    bench: Bench, reason: CloseReason
) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    closing = bench.close_by_protection(reason)

    position = OPENING.closed_by_protection(bench.flow, closing)
    assert bench.history.positions == [position]
    assert (position.reason, position.pnl, position.fees) == (reason, Decimal("-5.1"), Decimal("0.07"))
    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal("-5.1"), reason.value)]
    assert bench.exit_plans.current(bench.flow.id, "BTC") is None
    assert bench.cancellation.cancelled == [ProtectedPosition(bench.flow.assigned_account_id, "BTC")]


def test_a_closing_by_protection_the_flow_never_opened_is_told_and_logged(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.close_by_protection()

    assert bench.history.positions == []
    assert bench.notices.told == [(bench.flow.name.value, "BTC", Decimal("-5.1"), "stop loss")]
    (record,) = caplog.records
    assert record.getMessage() == "posizione chiusa da una protezione senza apertura del flusso"
    assert len(bench.cancellation.cancelled) == 1


def test_a_closing_by_protection_beyond_the_value_of_the_position_is_told_and_logged(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    bench.openings.openings[bench.flow.id, "BTC"] = OPENING

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.close_by_protection(realized_pnl=Decimal(-150))

    assert bench.history.positions == []
    (record,) = caplog.records
    assert record.getMessage() == "esito della chiusura per protezione non rappresentabile"
