from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.account_reconciliation import OutsideClosing
from autotrading.domain.flows.capital_change import require_increase_within, require_reduction_within
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.errors import (
    AllocatedCapitalNotPositiveError,
    ArchivedFlowNotModifiableError,
    CapitalAboveAvailableCapitalError,
    CapitalBelowFlowMinimumError,
    FlowCommandNotAllowedError,
)
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.free_capital import FreeCapital
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
OPENED_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
CLOSED_AT = datetime(2026, 11, 12, 12, 30, tzinfo=UTC)


@pytest.mark.parametrize("status", [FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_an_active_or_paused_flow_stops(status: FlowStatus) -> None:
    flow = a_flow(TENANT, status=status)

    assert flow.after(FlowCommand.STOP) == replace(flow, status=FlowStatus.STOPPED)


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ARCHIVED])
def test_a_stopped_or_archived_flow_does_not_stop_again(status: FlowStatus) -> None:
    with pytest.raises(FlowCommandNotAllowedError) as raised:
        a_flow(TENANT, status=status).after(FlowCommand.STOP)

    assert str(raised.value) == f"comando ferma non ammesso per un flusso {status.value}"


def test_a_new_capital_is_the_next_version_with_everything_else_kept() -> None:
    flow = a_flow(TENANT, status=FlowStatus.PAUSED, configuration=a_configuration(allocated_capital=Decimal(400)))

    changed = flow.with_capital(Decimal(700))

    assert changed == replace(
        flow, configuration=replace(flow.configuration, version=2, allocated_capital=Decimal(700))
    )


def test_an_archived_flow_keeps_its_capital() -> None:
    with pytest.raises(ArchivedFlowNotModifiableError):
        a_flow(TENANT, status=FlowStatus.ARCHIVED).with_capital(Decimal(700))


@pytest.mark.parametrize("capital", [Decimal(0), Decimal(-5)])
def test_a_capital_not_positive_is_refused(capital: Decimal) -> None:
    with pytest.raises(AllocatedCapitalNotPositiveError):
        a_flow(TENANT).with_capital(capital)


@pytest.mark.parametrize("capital", [Decimal(401), Decimal(1000)])
def test_a_raise_up_to_the_free_capital_plus_the_own_is_admitted(capital: Decimal) -> None:
    require_increase_within(Decimal(400), capital, FreeCapital(Decimal(600), "USDC"))


def test_a_raise_beyond_the_free_capital_plus_the_own_names_the_capital_available() -> None:
    with pytest.raises(CapitalAboveAvailableCapitalError) as raised:
        require_increase_within(Decimal(400), Decimal("1000.01"), FreeCapital(Decimal("600.00"), "USDC"))

    assert str(raised.value) == "capitale allocato oltre il capitale disponibile: 1000 USDC"
    assert raised.value.available == "1000 USDC"
    assert raised.value.status_code == 422


def state(capital: str, *, margin: str = "150", realized: str = "0", fees: str = "0") -> FlowState:
    flow = a_flow(TENANT, configuration=a_configuration(allocated_capital=Decimal(capital)))
    position = AccountPosition("BTC", TradeSide.LONG, Decimal(1), Decimal(margin), Decimal(0))
    return FlowState(flow.id, "USDC", Decimal(capital), (position,), Decimal(realized), Decimal(fees), Decimal(0))


@pytest.mark.parametrize("capital", ["150", "399"])
def test_a_reduction_down_to_the_committed_margin_is_admitted(capital: str) -> None:
    require_reduction_within(state(capital))


def test_a_reduction_below_the_committed_margin_names_the_minimum_of_the_flow() -> None:
    with pytest.raises(CapitalBelowFlowMinimumError) as raised:
        require_reduction_within(state("149.99", margin="150.000"))

    assert str(raised.value) == "capitale allocato sotto il minimo del flusso: 150 USDC"
    assert raised.value.minimum == "150 USDC"
    assert raised.value.status_code == 422


def test_the_minimum_of_the_flow_covers_its_realized_losses_and_fees() -> None:
    with pytest.raises(CapitalBelowFlowMinimumError) as raised:
        require_reduction_within(state("359.99", realized="-200", fees="10"))

    assert raised.value.minimum == "360 USDC"


def test_a_reduction_down_to_the_minimum_after_the_losses_is_admitted() -> None:
    require_reduction_within(state("360", realized="-200", fees="10"))


def test_the_realized_gains_lower_the_minimum_of_the_flow() -> None:
    require_reduction_within(state("100", realized="60", fees="10"))


def opening(side: TradeSide) -> PositionOpening:
    return PositionOpening(side, 2, Decimal(50), PositionEnd(Decimal(100000), OPENED_AT, OPENED_AT), Decimal("0.03"))


@pytest.mark.parametrize(
    ("side", "pnl", "price"),
    [
        (TradeSide.LONG, Decimal(2), Decimal(102000)),
        (TradeSide.LONG, Decimal(-50), Decimal(50000)),
        (TradeSide.SHORT, Decimal(2), Decimal(98000)),
    ],
)
def test_a_position_closed_outside_closes_at_the_price_its_pnl_implies(
    side: TradeSide, pnl: Decimal, price: Decimal
) -> None:
    flow = a_flow(TENANT)
    closing = OutsideClosing(flow.id, "BTC", "chiusa fuori dalla piattaforma", pnl, Decimal("0.05"), CLOSED_AT)

    closed = opening(side).closed_outside(flow, closing)

    assert (closed.closing, closed.pnl, closed.fees, closed.reason) == (
        PositionEnd(price, CLOSED_AT),
        pnl,
        Decimal("0.08"),
        CloseReason.OUTSIDE_PLATFORM,
    )


def test_a_position_closed_by_a_cycle_keeps_the_cycle_that_closed_it() -> None:
    flow = a_flow(TENANT)
    fill = ClosingFill(Decimal(101000), CLOSED_AT, Decimal("0.02"))

    closed = opening(TradeSide.LONG).closed(flow, "BTC", fill, CloseReason.AGENT, cycle=CLOSED_AT)

    assert closed.closing == PositionEnd(Decimal(101000), CLOSED_AT, CLOSED_AT)


def test_a_position_closed_keeps_the_result_the_exchange_reported() -> None:
    flow = a_flow(TENANT)
    fill = ClosingFill(Decimal(101000), CLOSED_AT, Decimal("0.02"), realized_pnl=Decimal("4.20"))

    closed = opening(TradeSide.LONG).closed(flow, "BTC", fill, CloseReason.FLOW_STOP)

    assert (closed.realized_pnl, closed.pnl) == (Decimal("4.20"), Decimal("4.20"))


def test_a_position_closed_without_a_reported_result_measures_the_price_move() -> None:
    flow = a_flow(TENANT)
    fill = ClosingFill(Decimal(101000), CLOSED_AT, Decimal("0.02"))

    closed = opening(TradeSide.LONG).closed(flow, "BTC", fill, CloseReason.AGENT)

    assert (closed.realized_pnl, closed.pnl) == (None, Decimal(1))


def test_a_position_closed_outside_keeps_the_result_the_exchange_reported() -> None:
    flow = a_flow(TENANT)
    closing = OutsideClosing(flow.id, "BTC", "chiusa fuori dalla piattaforma", Decimal(-7), Decimal("0.05"), CLOSED_AT)

    assert opening(TradeSide.LONG).closed_outside(flow, closing).realized_pnl == Decimal(-7)
