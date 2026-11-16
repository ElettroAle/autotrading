"""ADR incasso-dei-profitti: the checks of a cash-out, before any position closes."""

from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.cash_out import cash_out_capital
from autotrading.domain.flows.errors import CashOutCapitalOutOfRangeError, FlowWithoutProfitsError
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())


def state_worth(value: str, capital: str = "500") -> FlowState:
    flow = a_flow(TENANT, configuration=a_configuration(allocated_capital=Decimal(capital)))
    realized = Decimal(value) - Decimal(capital)
    return FlowState.attributed(flow, an_activity(), FlowTotals(flow.id, realized))


def test_without_a_capital_the_flow_keeps_the_capital_allocated_now() -> None:
    assert cash_out_capital("alfa", state_worth("620"), None) == Decimal(500)


def test_a_capital_between_zero_and_the_value_of_the_flow_is_the_new_capital() -> None:
    assert cash_out_capital("alfa", state_worth("618"), Decimal(400)) == Decimal(400)


@pytest.mark.parametrize("value", ["460", "500"])
def test_a_flow_worth_no_more_than_its_capital_has_no_profits(value: str) -> None:
    with pytest.raises(FlowWithoutProfitsError) as raised:
        cash_out_capital("alfa", state_worth(value), None)

    assert str(raised.value) == "alfa non ha profitti da incassare"
    assert raised.value.status_code == 409


@pytest.mark.parametrize("capital", ["0", "-1", "618", "700"])
def test_a_capital_out_of_zero_and_the_value_of_the_flow_is_refused(capital: str) -> None:
    with pytest.raises(CashOutCapitalOutOfRangeError) as raised:
        cash_out_capital("alfa", state_worth("618"), Decimal(capital))

    assert str(raised.value) == "il capitale indicato è maggiore di 0 e minore del valore del flusso, 618 USDC"
    assert raised.value.status_code == 400


def test_the_profits_are_checked_before_the_capital() -> None:
    with pytest.raises(FlowWithoutProfitsError):
        cash_out_capital("alfa", state_worth("500"), Decimal(0))
