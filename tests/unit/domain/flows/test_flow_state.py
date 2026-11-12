from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())


def flow_on(*assets: str, capital: Decimal = Decimal(500)) -> Flow:
    return a_flow(TENANT, configuration=a_configuration(assets=assets, allocated_capital=capital))


def totals_of(
    flow: Flow,
    *,
    realized_pnl: Decimal = Decimal(0),
    fees: Decimal = Decimal(0),
    funding: Decimal = Decimal(0),
) -> FlowTotals:
    return FlowTotals(flow.id, realized_pnl, fees, funding)


def test_the_flow_has_only_the_positions_on_its_assets() -> None:
    flow = flow_on("BTC", "SOL")
    activity = an_activity(positions=(a_position("BTC"), a_position("ETH"), a_position("SOL")))

    state = FlowState.attributed(flow, activity, totals_of(flow))

    assert [position.asset for position in state.positions] == ["BTC", "SOL"]


def test_realized_pnl_fees_and_funding_come_from_the_running_totals_of_the_ledger() -> None:
    flow = flow_on("BTC")

    state = FlowState.attributed(
        flow, an_activity(), totals_of(flow, realized_pnl=Decimal(40), fees=Decimal(2), funding=Decimal(-3))
    )

    assert (state.realized_pnl, state.fees, state.funding) == (Decimal(40), Decimal(2), Decimal(-3))


def test_the_liquidity_is_the_capital_plus_the_realized_pnl_and_funding_less_fees_and_margin() -> None:
    flow = flow_on("BTC")
    activity = an_activity(positions=(a_position("BTC", margin=Decimal(100)),))

    state = FlowState.attributed(
        flow, activity, totals_of(flow, realized_pnl=Decimal(40), fees=Decimal(2), funding=Decimal(-5))
    )

    assert state.margin == Decimal(100)
    assert state.available_liquidity == Decimal(433)


def test_the_total_value_adds_margin_and_unrealized_pnl_and_the_return_compares_it_with_the_capital() -> None:
    flow = flow_on("BTC", "SOL")
    activity = an_activity(
        positions=(
            a_position("BTC", margin=Decimal(60), unrealized_pnl=Decimal(8)),
            a_position("SOL", margin=Decimal(40), unrealized_pnl=Decimal(4)),
        ),
    )

    state = FlowState.attributed(flow, activity, totals_of(flow, realized_pnl=Decimal(38)))

    assert state.unrealized_pnl == Decimal(12)
    assert state.available_liquidity == Decimal(438)
    assert state.total_value == Decimal(550)
    assert state.return_percent == Decimal(10)


@pytest.mark.parametrize(("pnl", "expected"), [(Decimal(-50), Decimal(-10)), (Decimal(0), Decimal(0))])
def test_the_return_is_negative_on_a_loss_and_zero_without_operations(pnl: Decimal, expected: Decimal) -> None:
    flow = flow_on("BTC")

    state = FlowState.attributed(flow, an_activity(), totals_of(flow, realized_pnl=pnl))

    assert state.return_percent == expected


def test_a_flow_without_operations_keeps_its_capital_in_the_currency_of_the_account() -> None:
    flow = flow_on("BTC", capital=Decimal(1000))

    state = FlowState.attributed(flow, an_activity(), FlowTotals(flow.id))

    assert (state.flow_id, state.currency, state.allocated_capital) == (flow.id, "USDC", Decimal(1000))
    assert state.available_liquidity == state.total_value == Decimal(1000)
