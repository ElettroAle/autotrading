"""The money a flow may use in a cycle is the state attributed to it, within the margin the account has free."""

from decimal import Decimal

from autotrading.domain.flows.cycle_funds import CycleFunds
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
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
