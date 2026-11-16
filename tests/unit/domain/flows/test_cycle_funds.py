"""The money a flow may use in a cycle is the state attributed to it, within the margin the account has free."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.cycle_funds import CycleFunds
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.tenancy.user_id import UserId
from tests.support.activity import a_position

FLOW = FlowId.new()
PLENTY = Decimal(10000)


def attributed(
    *, realized_pnl: Decimal = Decimal(0), fees: Decimal = Decimal(0), margin: Decimal = Decimal(0)
) -> FlowState:
    positions = (a_position("BTC", margin=margin, unrealized_pnl=Decimal(12)),) if margin else ()
    return FlowState(FLOW, "USDC", Decimal(500), positions, realized_pnl, fees, Decimal(0))


def test_the_liquidity_is_the_one_attributed_to_the_flow() -> None:
    funds = CycleFunds(attributed(realized_pnl=Decimal(-100), fees=Decimal(2), margin=Decimal(50)), PLENTY)

    assert funds.available_liquidity == Decimal(348)


def test_the_liquidity_never_goes_beyond_the_margin_the_account_has_free() -> None:
    assert CycleFunds(attributed(), Decimal(200)).available_liquidity == Decimal(200)


def test_the_liquidity_never_goes_below_zero() -> None:
    assert CycleFunds(attributed(realized_pnl=Decimal(-600)), PLENTY).available_liquidity == Decimal(0)
    assert CycleFunds(attributed(), Decimal(-5)).available_liquidity == Decimal(0)


def test_the_value_is_the_attributed_one_whatever_the_free_margin() -> None:
    state = attributed(realized_pnl=Decimal(-100), fees=Decimal(2), margin=Decimal(50))

    assert CycleFunds(state, Decimal(1)).total_value == Decimal(410)


def test_the_return_keeps_two_decimals() -> None:
    assert CycleFunds(attributed(realized_pnl=Decimal(1)), PLENTY).return_percent == Decimal("0.20")
    assert str(CycleFunds(attributed(realized_pnl=Decimal("0.001")), PLENTY).return_percent) == "0.00"


def test_the_return_is_compounded_across_the_changes_of_the_capital() -> None:
    # ADR rendimento-composto-tra-le-variazioni-di-capitale: 10% up to an increase of 500 at 550, then 5%.
    increase = CapitalChange(
        FLOW,
        datetime(2026, 11, 16, 10, 0, tzinfo=UTC),
        Decimal(500),
        Decimal(1000),
        UserId("anna"),
        CapitalChangeReason.INCREASE,
        Decimal(500),
        value_before=Decimal(550),
    )
    state = replace(
        attributed(realized_pnl=Decimal("102.5")), allocated_capital=Decimal(1000), capital_changes=(increase,)
    )

    assert CycleFunds(state, PLENTY).return_percent == Decimal("15.50")


def test_no_return_is_measured_without_capital() -> None:
    assert CycleFunds(replace(attributed(), allocated_capital=Decimal(0)), PLENTY).return_percent is None
