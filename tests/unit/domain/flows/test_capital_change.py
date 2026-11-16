from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.activity import an_activity
from tests.support.flows import a_configuration, a_flow

NOW = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
USER = UserId("anna")


def state_worth(value: Decimal, capital: Decimal) -> FlowState:
    flow = a_flow(TenantId.new(), configuration=a_configuration(allocated_capital=capital))
    return FlowState.attributed(flow, an_activity(), FlowTotals(flow.id, value - capital))


@pytest.mark.parametrize(
    ("previous", "new", "reason", "amount"),
    [
        (Decimal(400), Decimal(700), CapitalChangeReason.INCREASE, Decimal(300)),
        (Decimal(700), Decimal(250), CapitalChangeReason.REDUCTION, Decimal(450)),
    ],
)
def test_a_change_asked_by_the_user_is_an_increase_or_a_reduction_by_its_amount(
    previous: Decimal, new: Decimal, reason: CapitalChangeReason, amount: Decimal
) -> None:
    change = CapitalChange.of(state_worth(Decimal(640), previous), new, NOW, USER)

    assert (change.reason, change.amount, change.value_before, change.cashed_profit) == (
        reason,
        amount,
        Decimal(640),
        Decimal(0),
    )


def test_the_reasons_read_as_the_history_names_them() -> None:
    assert [reason.value for reason in CapitalChangeReason] == ["aumento", "riduzione", "incasso"]


def test_a_cash_out_frees_the_value_above_the_new_capital_and_cashes_the_profit_above_the_old() -> None:
    state = state_worth(Decimal(618), Decimal(500))

    change = CapitalChange.cashed_out(state, Decimal(400), NOW, USER)

    assert change == CapitalChange(
        state.flow_id,
        NOW,
        Decimal(500),
        Decimal(400),
        USER,
        CapitalChangeReason.CASH_OUT,
        Decimal(218),
        value_before=Decimal(618),
        cashed_profit=Decimal(118),
    )
