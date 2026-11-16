"""ADR-chiusura-di-emergenza-per-ambito: the emergency closing reuses `CloseFlowPositionsUseCase`, the one way the
stop and the cash-out close the positions of a flow; it pauses through `AutomaticPausePort`, records itself through
`EmergencyClosingLogPort` in a table under row level security, and answers on two routes of the API.
"""

import ast
import re
from pathlib import Path
from typing import get_type_hints

import pytest

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.flows.cash_out_profits import CashOutPorts
from autotrading.application.flows.close_flow_positions import CloseFlowPositionsUseCase
from autotrading.application.flows.close_in_emergency import EmergencyClosingPorts
from autotrading.application.flows.ports import AutomaticPausePort, EmergencyClosingLogPort
from autotrading.application.flows.stop_flow import StopFlowUseCase
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.closed_position import CloseReason
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform

CANONICAL = "application/flows/close_flow_positions.py"
CLOSING_REQUEST = "PositionToClose"
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"

# A second copy of the closing of the positions of a flow, as the emergency closing would have written it.
A_COPY_OF_THE_CLOSING = """
class CloseInEmergencyUseCase:
    def _close(self, flow, asset, user_id):
        return self._positions.execute(PositionToClose(flow.assigned_account_id, asset, user_id))
"""
THROUGH_THE_SHARED_CLOSING = """
class CloseInEmergencyUseCase:
    def _close(self, flow, user_id):
        return self._ports.closings.execute(CloseFlowPositionsCommand(flow, user_id, CloseReason.EMERGENCY))
"""


def closings_outside_the_shared_one(module: SourceModule) -> list[str]:
    """Every request to close a position of a flow built outside the shared closing, as path and line."""
    if module.path == CANONICAL or not module.path.startswith("application/flows/"):
        return []
    return [
        f"src/autotrading/{module.path}:{node.lineno}"
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == CLOSING_REQUEST
    ]


def test_adr_chiusura_di_emergenza_the_positions_of_a_flow_close_only_in_the_shared_closing() -> None:
    found = [location for module in source_modules(SOURCE_ROOT) for location in closings_outside_the_shared_one(module)]

    assert found == [], (
        f"le posizioni di un flusso si chiudono solo con CloseFlowPositionsUseCase ({CANONICAL}): {found}"
    )


def test_adr_chiusura_di_emergenza_a_copy_of_the_closing_is_found() -> None:
    module = SourceModule.parse("application/flows/close_in_emergency.py", A_COPY_OF_THE_CLOSING)

    assert closings_outside_the_shared_one(module) == ["src/autotrading/application/flows/close_in_emergency.py:4"]


def test_adr_chiusura_di_emergenza_the_closing_through_the_shared_use_case_is_not_found() -> None:
    module = SourceModule.parse("application/flows/close_in_emergency.py", THROUGH_THE_SHARED_CLOSING)

    assert closings_outside_the_shared_one(module) == []


def test_adr_chiusura_di_emergenza_stop_cash_out_and_emergency_share_the_closing() -> None:
    assert get_type_hints(EmergencyClosingPorts)["closings"] is CloseFlowPositionsUseCase
    assert get_type_hints(CashOutPorts)["closings"] is CloseFlowPositionsUseCase
    assert get_type_hints(StopFlowUseCase.__init__)["closings"] is CloseFlowPositionsUseCase


def test_adr_chiusura_di_emergenza_pauses_and_records_through_the_ports_of_the_flows() -> None:
    hints = get_type_hints(EmergencyClosingPorts)

    assert (hints["pause"], hints["log"]) == (AutomaticPausePort, EmergencyClosingLogPort)
    assert CloseReason.EMERGENCY.value == "chiusura di emergenza"


def test_adr_chiusura_di_emergenza_the_record_lives_under_row_level_security() -> None:
    (migration,) = [path for path in MIGRATIONS.glob("*.py") if '"emergency_closings"' in path.read_text("utf-8")]
    text = migration.read_text("utf-8")

    assert "ALTER TABLE emergency_closings FORCE ROW LEVEL SECURITY" in text
    assert "CREATE POLICY emergency_closings_of_tenant ON emergency_closings" in text


@pytest.mark.parametrize(
    ("method", "path"),
    [("POST", "/flows/emergency-closings"), ("GET", "/flows/emergency-closings/preview")],
)
def test_adr_chiusura_di_emergenza_the_api_answers_on_its_routes(method: str, path: str) -> None:
    platform = Platform()
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        IdentityProvider().authentication(),
    )

    assert method.lower() in api.openapi()["paths"][path]


def admitted_reasons(migrations: list[str]) -> set[str]:
    """The closing reasons the last migration that defines the check on the history admits."""
    defining = [text for text in migrations if "closed_positions_reason_known" in text]
    module = ast.parse(defining[-1])
    texts = [
        node.value
        for node in ast.walk(module)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "'" in node.value
    ]
    return {reason for text in texts for reason in re.findall(r"'([a-z_]+)'", text)}


def test_adr_chiusura_di_emergenza_the_history_admits_every_closing_reason() -> None:
    migrations = [path.read_text("utf-8") for path in sorted(MIGRATIONS.glob("*.py"))]

    assert {reason.name.lower() for reason in CloseReason} <= admitted_reasons(migrations)


def test_adr_chiusura_di_emergenza_a_reason_the_history_does_not_admit_is_found() -> None:
    migration = "REASONS = \"'agent', 'manual'\"\nop.create_check_constraint(\"closed_positions_reason_known\")"

    assert admitted_reasons([migration]) == {"agent", "manual"}
