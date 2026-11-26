"""ADR-stop-e-obiettivo-in-vigore-nello-stato-della-posizione: the one reading of the state of a flow composes the plan
in force of every open position from the levels of the protections recorded, by a rule of the domain in one point; at
the start of the cycle, after the account and before the state, the worker records the protections waiting on the
exchange of a position without protections recorded, through a use case of the orders context that shares the reading
of the protections with the protection of the open positions; the API never reads the exchange for them.
"""

import ast
import inspect
from pathlib import Path
from typing import get_type_hints

from autotrading import bootstrap
from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts
from autotrading.application.flows import ports as flow_ports
from autotrading.application.flows import read_flow_state
from autotrading.application.flows.read_cycle_flow import CycleAccountReadings, ReadCycleFlowUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.orders import ports as order_ports
from autotrading.application.orders.record_waiting_protections import RecordWaitingProtectionsUseCase
from autotrading.application.orders.sending import held_protections
from autotrading.domain.flows.exit_plan import ExitPlan

ORDERS = Path(inspect.getfile(order_ports)).parent
READING_MODULE = "sending.py"
RECORDING = RecordWaitingProtectionsUseCase.__name__


def _calls(source: str) -> list[str]:
    """The names called in the source, in the order they appear."""
    nodes = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
    ordered = sorted(nodes, key=lambda node: (node.lineno, node.col_offset))
    return [_name(node.func) for node in ordered]


def _called_paths(source: str) -> list[str]:
    """What the source calls, written as in the source, in the order the calls are made."""
    nodes = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
    ordered = sorted(nodes, key=lambda node: (node.lineno, node.col_offset))
    return [ast.unparse(node.func) for node in ordered]


def _name(function: ast.expr) -> str:
    if isinstance(function, ast.Attribute):
        return function.attr
    return function.id if isinstance(function, ast.Name) else ""


def _readers_of_waiting_protections(sources: dict[str, str]) -> list[str]:
    """The modules that read the protections waiting on the exchange themselves."""
    return sorted(name for name, source in sources.items() if "active" in _calls(source))


def _sources_of_orders() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in ORDERS.glob("*.py")}


def test_adr_stop_e_obiettivo_in_vigore_the_one_reading_of_the_state_reads_the_protections_recorded() -> None:
    hints = get_type_hints(ReadFlowStateUseCase.__init__)

    assert hints["protection_levels"] is flow_ports.FlowProtectionLevelsPort
    assert get_type_hints(TenantPorts)["protection_levels"] is flow_ports.FlowProtectionLevelsPort


def test_adr_stop_e_obiettivo_in_vigore_the_plan_in_force_is_composed_by_the_domain_in_one_point() -> None:
    reading = inspect.getsource(read_flow_state)

    assert "in_force" in _calls(reading)
    assert "ExitPlan" in _calls(reading)
    assert "in_force" in _calls(inspect.getsource(ExitPlan.updated).strip())
    assert "placed_levels" in _calls(reading)


def test_adr_stop_e_obiettivo_in_vigore_the_protections_are_recorded_after_the_account_and_before_the_state() -> None:
    called = _called_paths(inspect.getsource(ReadCycleFlowUseCase.execute).strip())
    account, recording, state = (
        called.index("self._account.account.execute"),
        called.index("self._account.waiting_protections.execute"),
        called.index("self._read_state.execute"),
    )

    assert get_type_hints(CycleAccountReadings)["waiting_protections"] is flow_ports.WaitingProtectionsPort
    assert account < recording < state


def test_adr_stop_e_obiettivo_in_vigore_a_use_case_of_orders_records_the_protections_waiting() -> None:
    hints = get_type_hints(RecordWaitingProtectionsUseCase.__init__)

    assert hints["protections"] is order_ports.ProtectionRepositoryPort
    assert str(hints["exchanges"]).endswith("ExchangeConnection]")
    assert get_type_hints(RecordWaitingProtectionsUseCase.execute)["held"] is order_ports.HeldFlowAssetsPort


def test_adr_stop_e_obiettivo_in_vigore_the_reading_of_the_protections_waiting_is_shared() -> None:
    sources = _sources_of_orders()

    assert _readers_of_waiting_protections(sources) == [READING_MODULE]
    assert "active" in _calls(inspect.getsource(held_protections))
    assert held_protections.__name__ in _calls(sources["protect_open_positions.py"])
    assert held_protections.__name__ in _calls(sources["record_waiting_protections.py"])


def test_adr_stop_e_obiettivo_in_vigore_a_second_reading_of_the_protections_waiting_violates() -> None:
    module = "protect_open_positions.py"
    repeated = "def _unprotected(account, asset):\n    return account.exchange.protections.active(account.access)\n"

    assert _readers_of_waiting_protections({module: repeated}) == [module]


def test_adr_stop_e_obiettivo_in_vigore_the_api_never_reads_the_exchange_for_the_levels() -> None:
    api_composition = inspect.getsource(bootstrap.tenant_use_cases)

    assert RECORDING not in api_composition
    assert RECORDING not in inspect.getsource(inspect.getmodule(TenantPorts) or bootstrap)
    assert RECORDING in inspect.getsource(bootstrap)
