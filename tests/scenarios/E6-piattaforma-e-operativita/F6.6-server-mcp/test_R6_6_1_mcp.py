"""R6.6.1: the flows of the user through the MCP server, reached by the client of the SDK over Streamable HTTP, on the
use cases of the API built with the fake adapters (ADR server-mcp-in-un-container-proprio-con-accesso-entra). What the
dashboard shows is what the API answers on the same platform: the client gets the same values and the same errors.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from mcp.types import CallToolResult, Tool
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.activity import a_position, an_activity
from tests.support.api_session import ApiSession
from tests.support.flow_cycles import FlowCycles, at
from tests.support.mcp_session import INITIALIZE, METADATA_URL, McpSession, body_of, credential_exposures
from tests.support.problems import reason_of
from tests.support.steps import quoted
from tests.support.steps_r6_6_1_entra import *  # noqa: F403 - the steps of the Entra settings, same story

scenarios(
    "E6-piattaforma-e-operativita/F6.6-server-mcp/R6.6.1-gestione-dei-flussi-via-mcp/mcp/R6.6.1-gestione-dei-flussi-via-mcp.feature"
)

# Far above the balance of the account, 1000 USDC: no free capital covers it (R1.1.7).
CAPITAL_ABOVE_BALANCE = "1000000"


@dataclass
class Session:
    """The flows of two users on one platform, the MCP server and the API in front of it, and what the client got."""

    flow_cycles: FlowCycles = field(default_factory=FlowCycles)
    user: str = ""
    name: str = ""
    results: dict[str, CallToolResult] = field(default_factory=dict)
    tools: list[Tool] = field(default_factory=list)
    refused: list[tuple[int, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.mcp = McpSession(self.flow_cycles.platform)
        self.api = ApiSession(self.flow_cycles.platform)

    def flow(self, name: str) -> Flow:
        return self.flow_cycles.flow(name)

    def flow_id(self, name: str) -> str:
        return str(self.flow(name).id.value)

    def call(self, tool: str, arguments: Mapping[str, object] | None = None) -> CallToolResult:
        self.results[tool] = self.mcp.call_as(self.user, tool, arguments)
        return self.results[tool]

    def body(self, tool: str) -> dict[str, Any]:
        result = self.results[tool]
        assert not result.is_error, body_of(result)
        return body_of(result)

    def problem(self, tool: str) -> dict[str, Any]:
        result = self.results[tool]
        assert result.is_error, body_of(result)
        return body_of(result)


@pytest.fixture
def session() -> Session:
    return Session()


def with_history(session: Session, name: str) -> None:
    """A completed cycle, then an open position on the account and a closed position: what the pages of the flow
    show."""
    flow_cycles = session.flow_cycles
    flow_cycles.run(name, "10:00")
    flow = session.flow(name)
    platform = flow_cycles.platform
    platform.account_activity.activities[flow.assigned_account_id] = an_activity(
        positions=(a_position("BTC", margin=Decimal(20), unrealized_pnl=Decimal("1.5"), mark_price=Decimal(101)),)
    )
    closed_at = at("09:30")
    platform.closed_positions.positions.append(
        ClosedPosition(
            tenant_id=flow.tenant_id,
            flow_id=flow.id,
            asset="BTC",
            side=TradeSide.LONG,
            leverage=2,
            margin=Decimal(50),
            opening=PositionEnd(Decimal(100), closed_at - timedelta(hours=1)),
            closing=PositionEnd(Decimal(104), closed_at),
            fees=Decimal("0.2"),
            reason=CloseReason.AGENT,
        )
    )


@given(quoted('che "{first}" ha i flussi "{one}" e "{other}" e "{second}" ha il flusso "{third}"'))
def flows_of_two_users(  # noqa: PLR0917 - one argument per value of the step
    session: Session, first: str, one: str, other: str, second: str, third: str
) -> None:
    flow_cycles = session.flow_cycles
    flow_cycles.add_flow(first, one, assets=("BTC",))
    flow_cycles.add_flow(first, other, assets=("ETH",))
    flow_cycles.add_flow(second, third, assets=("BTC",))
    with_history(session, one)


@given(quoted('che "{user}" ha collegato un client MCP con il suo accesso Entra'))
def client_connected(session: Session, user: str) -> None:
    session.user = user


@when("il client chiede l'elenco dei flussi")
def list_flows(session: Session) -> None:
    session.call("list_flows")


@then(quoted('riceve "{one}" e "{other}" con stato, valore e PnL dall\'avvio'))
def flows_received(session: Session, one: str, other: str) -> None:
    listed = session.body("list_flows")["flows"]
    assert isinstance(listed, list)
    by_name = {flow["name"]: flow for flow in listed}
    api_flows = {flow["name"]: flow for flow in session.api.get_as(session.user, "/flows/overview").json()}

    assert set(by_name) == {one, other}
    for name in (one, other):
        shown = api_flows[name]
        assert (by_name[name]["status"], by_name[name]["current_capital"]) == (
            shown["status"],
            shown["current_capital"],
        )
        assert by_name[name]["summary"]["total_gain"] == shown["summary"]["total_gain"]


@when(quoted('il client di "{user}" chiede posizioni, cicli e statistiche del flusso "{name}"'))
def flow_data(session: Session, user: str, name: str) -> None:
    session.user = user
    flow_id = session.flow_id(name)
    session.call("read_flow_state", {"flow_id": flow_id})
    session.call("list_closed_positions", {"flow_id": flow_id})
    session.call("list_cycles", {"flow_id": flow_id})
    session.call("read_flow_statistics", {"flow_id": flow_id})


@then(quoted('riceve gli stessi valori che la dashboard mostra per "{name}"'))
def same_values_as_the_dashboard(session: Session, name: str) -> None:
    flow_id = session.flow_id(name)
    shown = {
        "state": session.api.get_as(session.user, f"/flows/{flow_id}/state").json(),
        "closed": session.api.get_as(session.user, f"/flows/{flow_id}/closed-positions").json(),
        "cycles": session.api.get_as(session.user, f"/flows/{flow_id}/cycles").json(),
        "statistics": session.api.get_as(session.user, f"/flows/{flow_id}/statistics").json(),
    }

    assert session.body("read_flow_state")["positions"] == shown["state"]["positions"]
    assert shown["state"]["positions"], "la dashboard non mostra posizioni aperte"
    assert session.body("list_closed_positions") == shown["closed"]
    assert session.body("list_cycles") == shown["cycles"]
    assert session.body("read_flow_statistics") == shown["statistics"]


@when(quoted('il client di "{user}" mette in pausa il flusso "{name}"'))
def pause_flow(session: Session, user: str, name: str) -> None:
    session.user = user
    session.call("pause_flow", {"flow_id": session.flow_id(name)})


@then(quoted('il flusso "{name}" risulta in pausa come se l\'avesse fatto dalla dashboard'))
def flow_paused(session: Session, name: str) -> None:
    shown = session.api.get_as(session.user, f"/flows/{session.flow_id(name)}").json()

    assert session.body("pause_flow")["status"] == FlowStatus.PAUSED.value
    assert shown["status"] == FlowStatus.PAUSED.value
    assert session.flow(name).status is FlowStatus.PAUSED


@when(quoted('il client di "{user}" cambia il capitale del flusso "{name}" oltre il saldo del conto'))
def capital_above_balance(session: Session, user: str, name: str) -> None:
    session.user, session.name = user, name
    arguments = {"flow_id": session.flow_id(name), "allocated_capital": CAPITAL_ABOVE_BALANCE}
    session.call("change_allocated_capital", arguments)


@then("riceve lo stesso errore che l'API restituisce")
def same_error_as_the_api(session: Session) -> None:
    answer = session.api.put_as(
        session.user,
        f"/flows/{session.flow_id(session.name)}/allocated-capital",
        {"allocated_capital": CAPITAL_ABOVE_BALANCE},
    )
    problem = session.problem("change_allocated_capital")

    assert problem["status"] == answer.status_code
    assert {name: value for name, value in problem.items() if name not in {"type", "title", "status"}} == reason_of(
        answer
    )


@when(quoted('il client di "{user}" chiede o modifica il flusso "{name}"'))
def foreign_flow(session: Session, user: str, name: str) -> None:
    session.user = user
    flow_id = session.flow_id(name)
    session.call("get_flow", {"flow_id": flow_id})
    session.call("pause_flow", {"flow_id": flow_id})


@then(quoted('riceve l\'errore "{reason}"'))
def error_received(session: Session, reason: str) -> None:
    assert session.problem("get_flow")["detail"] == reason
    assert session.problem("pause_flow")["detail"] == reason
    assert session.flow("gamma").status is FlowStatus.ACTIVE


@when("un client MCP senza token valido chiede l'elenco dei flussi")
def client_without_access(session: Session) -> None:
    call = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_flows", "arguments": {}}}
    for request, headers in (
        (INITIALIZE, {}),
        (call, {}),
        (call, {"Authorization": "Bearer not-a-token"}),
    ):
        answer = session.mcp.post("/mcp", request, headers)
        session.refused.append((answer.status_code, answer.headers.get("www-authenticate", "")))


@then("la richiesta è rifiutata come non autenticata")
def refused_as_not_authenticated(session: Session) -> None:
    assert [status for status, _ in session.refused] == [401, 401, 401]
    assert all(f'resource_metadata="{METADATA_URL}"' in challenge for _, challenge in session.refused)


@when(quoted('il client di "{user}" elenca gli strumenti disponibili'))
def tools_listed(session: Session, user: str) -> None:
    session.tools = session.mcp.tools_as(user)


@then("nessuno strumento legge o modifica le credenziali di un conto, di una fonte o di un fornitore IA")
def no_credential_tool(session: Session) -> None:
    assert session.tools
    assert credential_exposures(session.tools) == []
