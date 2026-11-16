"""ADR capitale-libero-al-netto-del-valore-dei-flussi: the free capital is the balance less the total value of the
flows holding the account, so the gains and losses of a flow stay its own until it cashes them out."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.errors import CapitalAboveFreeCapitalError
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.free_capital import FreeCapital, allocated_capital_of_account
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
CASHED_AT = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)


def state_of(capital: str, *, realized_pnl: str = "0", unrealized_pnl: str = "0", cashed: str = "0") -> FlowState:
    flow = a_flow(TENANT, account_id=ACCOUNT, configuration=a_configuration(allocated_capital=Decimal(capital)))
    activity = an_activity(positions=(a_position("BTC", unrealized_pnl=Decimal(unrealized_pnl)),))
    capital_value = Decimal(capital)
    cash_out = CapitalChange(
        flow.id,
        CASHED_AT,
        capital_value,
        capital_value,
        UserId("anna"),
        CapitalChangeReason.CASH_OUT,
        Decimal(cashed),
        value_before=capital_value + Decimal(cashed),
        cashed_profit=Decimal(cashed),
    )
    changes = (cash_out,) if Decimal(cashed) else ()
    return FlowState.attributed(flow, activity, FlowTotals(flow.id, Decimal(realized_pnl)), capital_changes=changes)


def test_the_free_capital_takes_off_the_balance_the_total_value_of_every_flow() -> None:
    states = (state_of("300", realized_pnl="70"), state_of("200", unrealized_pnl="-50"))

    assert FreeCapital.of(Decimal(1000), "USDC", states) == FreeCapital(Decimal(480), "USDC")


def test_a_profit_cashed_out_is_free_capital_again() -> None:
    cashed_out = state_of("500", realized_pnl="118", cashed="118")

    assert FreeCapital.of(Decimal(1118), "USDC", (cashed_out,)) == FreeCapital(Decimal(618), "USDC")


def test_an_account_without_flows_has_its_whole_balance_free() -> None:
    assert FreeCapital.of(Decimal(1000), "USDC", ()) == FreeCapital(Decimal(1000), "USDC")


def test_a_capital_beyond_the_free_capital_is_refused_with_the_free_capital() -> None:
    with pytest.raises(CapitalAboveFreeCapitalError) as raised:
        FreeCapital(Decimal(630), "USDC").require_room_for(Decimal(700))

    assert str(raised.value) == "capitale allocato oltre il capitale libero: 630 USDC"


def test_a_capital_up_to_the_free_capital_has_room() -> None:
    FreeCapital(Decimal(630), "USDC").require_room_for(Decimal(630))


def test_the_allocated_capital_of_an_account_sums_only_its_flows_holding_it() -> None:
    held = a_flow(TENANT, status=FlowStatus.ACTIVE, account_id=ACCOUNT)
    archived = a_flow(TENANT, status=FlowStatus.ARCHIVED, account_id=ACCOUNT)
    elsewhere = a_flow(TENANT, status=FlowStatus.ACTIVE)

    assert allocated_capital_of_account(ACCOUNT, (held, archived, elsewhere)) == Decimal(100)
