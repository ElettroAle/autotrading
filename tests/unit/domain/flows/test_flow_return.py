from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.flow_return import FlowReturn
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow


@pytest.mark.parametrize(
    ("initial", "current", "percent"),
    [
        ("300", "330", "10.00"),
        ("300", "270", "-10.00"),
        ("300", "300", "0.00"),
        ("300", "301", "0.33"),
        ("300", "300.0049", "0.00"),
        ("300", "299.9999", "0.00"),
    ],
)
def test_the_return_is_the_change_of_the_capital_in_percent_with_two_decimals(
    initial: str, current: str, percent: str
) -> None:
    flow_return = FlowReturn(Decimal(initial), Decimal(current))

    assert str(flow_return.percent) == percent


def test_the_return_is_not_available_without_initial_capital() -> None:
    assert FlowReturn(Decimal(0), Decimal(10)).percent is None


def test_the_return_of_a_state_measures_its_total_value_against_the_capital_allocated_now() -> None:
    flow = a_flow(TenantId(uuid4()), configuration=a_configuration(assets=("BTC",), allocated_capital=Decimal(300)))
    activity = an_activity(positions=(a_position("BTC", margin=Decimal(50), unrealized_pnl=Decimal(20)),))
    state = FlowState.attributed(flow, activity, FlowTotals(flow.id, Decimal(15), Decimal(5), Decimal(0)))

    flow_return = FlowReturn.of(state)

    assert (flow_return.initial_capital, flow_return.current_capital) == (Decimal(300), Decimal(330))
    assert flow_return.percent == Decimal("10.00")
