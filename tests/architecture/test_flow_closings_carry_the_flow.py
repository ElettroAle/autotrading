"""ADR-chiusure-dei-flussi-con-il-flusso-nell-ordine: the closing orders of a stop, a cash-out and an emergency closing
carry the flow they close, from `CloseFlowPositionsUseCase` through the orders context and the worker to the order
recorded; a manual command closes for no flow. The ledger then gives their executions to the flow of the order (ADR
0063), whatever flow holds the asset when it reads them.
"""

import ast
import inspect
from typing import get_type_hints
from uuid import UUID

from autotrading.adapters.inbound.api.worker import PositionClosingRequest
from autotrading.application.flows.ports import PositionToClose
from autotrading.application.orders.ports import FlowPositionToClosePort, PositionClosingPort
from autotrading.domain.orders.order import OrderSource
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

CLOSING_REQUEST = "PositionToClose"
# Account, asset, user and flow.
CLOSING_ARGUMENTS = 4

WITHOUT_THE_FLOW = """
def _close(self, flow, asset, command):
    return self._ports.positions.execute(PositionToClose(flow.assigned_account_id, asset, command.user_id))
"""
WITH_THE_FLOW = """
def _close(self, flow, asset, command):
    position = PositionToClose(flow.assigned_account_id, asset, command.user_id, flow.id.value)
    return self._ports.positions.execute(position)
"""
WITH_THE_FLOW_BY_NAME = """
def _close(self, flow, asset, command):
    return PositionToClose(flow.assigned_account_id, asset, command.user_id, flow_id=flow.id.value)
"""


def closings_without_the_flow(module: SourceModule) -> list[str]:
    """Every request to close a position of a flow that does not name the flow, as path and line."""
    return [
        f"src/autotrading/{module.path}:{node.lineno}"
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == CLOSING_REQUEST
        and len(node.args) < CLOSING_ARGUMENTS
        and "flow_id" not in {keyword.arg for keyword in node.keywords}
    ]


def test_adr_chiusure_dei_flussi_every_closing_of_a_flow_names_the_flow() -> None:
    found = [location for module in source_modules(SOURCE_ROOT) for location in closings_without_the_flow(module)]

    assert found == [], f"una chiusura di un flusso porta il flusso che chiude: {found}"


def test_adr_chiusure_dei_flussi_a_closing_without_the_flow_is_found() -> None:
    module = SourceModule.parse("application/flows/close_flow_positions.py", WITHOUT_THE_FLOW)

    assert closings_without_the_flow(module) == ["src/autotrading/application/flows/close_flow_positions.py:3"]


def test_adr_chiusure_dei_flussi_a_closing_with_the_flow_is_not_found() -> None:
    for source in (WITH_THE_FLOW, WITH_THE_FLOW_BY_NAME):
        module = SourceModule.parse("application/flows/close_flow_positions.py", source)

        assert closings_without_the_flow(module) == []


def test_adr_chiusure_dei_flussi_the_flow_goes_from_the_flows_to_the_worker() -> None:
    assert get_type_hints(PositionToClose)["flow_id"] is UUID
    asked = inspect.getattr_static(FlowPositionToClosePort, "flow_id")
    assert isinstance(asked, property)
    assert get_type_hints(asked.fget)["return"] is UUID
    assert get_type_hints(PositionClosingPort.close)["flow_id"] == UUID | None
    assert "flow_id" in inspect.signature(PositionClosingPort.close).parameters


def test_adr_chiusure_dei_flussi_the_worker_takes_the_flow_as_optional() -> None:
    field = PositionClosingRequest.model_fields["flow_id"]

    assert field.annotation == UUID | None
    assert not field.is_required()


def test_adr_chiusure_dei_flussi_the_order_keeps_the_flow_it_closes_beside_the_link_of_the_cycle() -> None:
    hints = get_type_hints(OrderSource)

    assert hints["closing_flow_id"] == UUID | None
    assert isinstance(inspect.getattr_static(OrderSource, "flow_id"), property)
