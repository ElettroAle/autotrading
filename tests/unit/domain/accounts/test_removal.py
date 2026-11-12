from decimal import Decimal

import pytest

from autotrading.domain.accounts.errors import (
    FlowPositionsLeftOpenError,
    OpenPositionsNeedConfirmationError,
    OperatingFlowsNeedConfirmationError,
)
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.accounts.removal import (
    FlowPositionLeftOpen,
    require_all_closed,
    require_confirmation_for,
    require_confirmation_for_flows,
)

SHORT_ETH = Position("ETH", PositionSide.SHORT, Decimal("1.5"), 3, Decimal(3000), Decimal("-4.2"), None)


def test_an_account_without_positions_needs_no_confirmation() -> None:
    require_confirmation_for(())


def test_an_account_with_any_open_position_needs_confirmation() -> None:
    with pytest.raises(OpenPositionsNeedConfirmationError):
        require_confirmation_for((SHORT_ETH,))


def test_an_account_without_operating_flows_needs_no_confirmation() -> None:
    require_confirmation_for_flows(())


@pytest.mark.parametrize(("flows", "listed"), [(["alfa"], "alfa"), (["alfa", "beta"], "alfa, beta")])
def test_an_account_with_operating_flows_needs_a_confirmation_naming_them(flows: list[str], listed: str) -> None:
    with pytest.raises(OperatingFlowsNeedConfirmationError) as raised:
        require_confirmation_for_flows(flows)

    assert raised.value.flows == tuple(flows)
    assert str(raised.value) == f"il conto ha flussi attivi o in pausa che verranno fermati: {listed}"
    assert raised.value.status_code == 409


def test_an_account_whose_flow_positions_all_closed_can_be_removed() -> None:
    require_all_closed(())


def test_a_flow_position_left_open_keeps_the_account_naming_it_with_its_reason() -> None:
    left_open = (FlowPositionLeftOpen("BTC", "Order rejected"), FlowPositionLeftOpen("ETH", "margine insufficiente"))

    with pytest.raises(FlowPositionsLeftOpenError) as raised:
        require_all_closed(left_open)

    assert raised.value.positions == (("BTC", "Order rejected"), ("ETH", "margine insufficiente"))
    assert raised.value.status_code == 409
    assert str(raised.value) == (
        "posizioni dei flussi rimaste aperte, conto non rimosso: BTC (Order rejected), ETH (margine insufficiente)"
    )
