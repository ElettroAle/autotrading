from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import a_fill, a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())


def flow_on(*assets: str, capital: Decimal = Decimal(500)) -> Flow:
    return a_flow(TENANT, configuration=a_configuration(assets=assets, allocated_capital=capital))


def test_the_flow_has_only_the_positions_on_its_assets() -> None:
    flow = flow_on("BTC", "SOL")
    activity = an_activity(positions=(a_position("BTC"), a_position("ETH"), a_position("SOL")))

    state = FlowState.attributed(flow, activity, frozenset())

    assert [position.asset for position in state.positions] == ["BTC", "SOL"]


def test_only_the_fills_of_the_orders_of_the_flow_count() -> None:
    flow, own, other = flow_on("BTC"), uuid4(), uuid4()
    fills = (
        a_fill("BTC", own, realized_pnl=Decimal(40), fee=Decimal(2)),
        a_fill("BTC", other, realized_pnl=Decimal(7), fee=Decimal(1)),
        a_fill("BTC", None, realized_pnl=Decimal(9), fee=Decimal(3)),
    )

    state = FlowState.attributed(flow, an_activity(fills=fills), frozenset({own}))

    assert (state.realized_pnl, state.fees) == (Decimal(40), Decimal(2))


def test_the_fills_of_the_flow_add_up() -> None:
    flow, first, second = flow_on("BTC"), uuid4(), uuid4()
    fills = (
        a_fill("BTC", first, realized_pnl=Decimal(40), fee=Decimal(2)),
        a_fill("BTC", second, realized_pnl=Decimal(-10), fee=Decimal(1)),
    )

    state = FlowState.attributed(flow, an_activity(fills=fills), frozenset({first, second}))

    assert (state.realized_pnl, state.fees) == (Decimal(30), Decimal(3))


def test_the_liquidity_is_the_capital_plus_the_realized_pnl_less_fees_and_margin() -> None:
    flow, order = flow_on("BTC"), uuid4()
    activity = an_activity(
        positions=(a_position("BTC", margin=Decimal(100)),),
        fills=(a_fill("BTC", order, realized_pnl=Decimal(40), fee=Decimal(2)),),
    )

    state = FlowState.attributed(flow, activity, frozenset({order}))

    assert state.margin == Decimal(100)
    assert state.available_liquidity == Decimal(438)


def test_the_total_value_adds_margin_and_unrealized_pnl_and_the_return_compares_it_with_the_capital() -> None:
    flow, order = flow_on("BTC", "SOL"), uuid4()
    activity = an_activity(
        positions=(
            a_position("BTC", margin=Decimal(60), unrealized_pnl=Decimal(8)),
            a_position("SOL", margin=Decimal(40), unrealized_pnl=Decimal(4)),
        ),
        fills=(a_fill("BTC", order, realized_pnl=Decimal(38)),),
    )

    state = FlowState.attributed(flow, activity, frozenset({order}))

    assert state.unrealized_pnl == Decimal(12)
    assert state.available_liquidity == Decimal(438)
    assert state.total_value == Decimal(550)
    assert state.return_percent == Decimal(10)


@pytest.mark.parametrize(("pnl", "expected"), [(Decimal(-50), Decimal(-10)), (Decimal(0), Decimal(0))])
def test_the_return_is_negative_on_a_loss_and_zero_without_operations(pnl: Decimal, expected: Decimal) -> None:
    flow, order = flow_on("BTC"), uuid4()

    state = FlowState.attributed(flow, an_activity(fills=(a_fill("BTC", order, realized_pnl=pnl),)), frozenset({order}))

    assert state.return_percent == expected


def test_a_flow_without_operations_keeps_its_capital_in_the_currency_of_the_account() -> None:
    flow = flow_on("BTC", capital=Decimal(1000))

    state = FlowState.attributed(flow, an_activity(), frozenset())

    assert (state.flow_id, state.currency, state.allocated_capital) == (flow.id, "USDC", Decimal(1000))
    assert state.available_liquidity == state.total_value == Decimal(1000)
