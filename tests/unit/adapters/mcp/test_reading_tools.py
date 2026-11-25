"""Each reading tool answers what the reading of the API answers, on the same use case of the tenant."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest

from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry, MemoryOutcome
from autotrading.domain.flows.recorded_decision import DecisionAction
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.activity import a_position, an_activity
from tests.support.api_session import ApiSession
from tests.support.flow_cycles import FlowCycles, at
from tests.support.mcp_session import McpSession, body_of


class Flows:
    """Two flows of anna, one with a cycle, a closed position and an open one, read by the server and by the API."""

    def __init__(self) -> None:
        self.cycles = FlowCycles()
        self.alfa = self.cycles.add_flow("anna", "alfa", assets=("BTC",))
        self.cycles.add_flow("anna", "beta", assets=("ETH",))
        self.cycles.run("alfa", "10:00")
        platform = self.cycles.platform
        platform.account_activity.activities[self.alfa.assigned_account_id] = an_activity(
            positions=(a_position("BTC", margin=Decimal(20), unrealized_pnl=Decimal(2), mark_price=Decimal(102)),)
        )
        closed_at = at("09:00")
        platform.closed_positions.positions.append(
            ClosedPosition(
                tenant_id=self.alfa.tenant_id,
                flow_id=self.alfa.id,
                asset="BTC",
                side=TradeSide.SHORT,
                leverage=3,
                margin=Decimal(30),
                opening=PositionEnd(Decimal(100), closed_at - timedelta(minutes=30)),
                closing=PositionEnd(Decimal(98), closed_at),
                fees=Decimal("0.1"),
                reason=CloseReason.AGENT,
            )
        )
        self.mcp = McpSession(platform)
        self.api = ApiSession(platform)
        self.flow_id = str(self.alfa.id.value)

    def read(self, tool: str, arguments: Mapping[str, object] | None = None) -> dict[str, Any]:
        result = self.mcp.call_as("anna", tool, arguments)
        assert not result.is_error, body_of(result)
        return body_of(result)

    def shown(self, path: str) -> Any:
        answer = self.api.get_as("anna", path)
        assert answer.status_code == 200, answer.text
        return answer.json()


@pytest.fixture(scope="module")
def flows() -> Flows:
    return Flows()


def test_the_list_of_the_flows_is_the_overview_of_the_api(flows: Flows) -> None:
    assert flows.read("list_flows")["flows"] == flows.shown("/flows/overview")


def test_the_list_of_the_flows_takes_the_period(flows: Flows) -> None:
    assert flows.read("list_flows", {"period": "24h"})["flows"] == flows.shown("/flows/overview?period=24h")


def test_a_flow_is_read_with_its_configuration(flows: Flows) -> None:
    flow = flows.read("get_flow", {"flow_id": flows.flow_id})
    shown = flows.shown(f"/flows/{flows.flow_id}")
    assert isinstance(shown, dict)

    assert {name: value for name, value in flow.items()} == {
        name: value for name, value in shown.items() if name != "system_prompt_placeholders"
    }


def test_the_state_of_a_flow_is_the_state_of_the_api(flows: Flows) -> None:
    assert flows.read("read_flow_state", {"flow_id": flows.flow_id}) == flows.shown(f"/flows/{flows.flow_id}/state")


def test_the_closed_positions_take_the_filters(flows: Flows) -> None:
    arguments = {"flow_id": flows.flow_id, "filters": {"side": "short", "result": "vinta"}}

    page = flows.read("list_closed_positions", arguments)

    assert page == flows.shown(f"/flows/{flows.flow_id}/closed-positions?side=short&result=vinta")
    assert page["total"] == 1


def test_the_cycles_take_the_filters(flows: Flows) -> None:
    page = flows.read("list_cycles", {"flow_id": flows.flow_id, "filters": {"outcome": "concluso"}})

    assert page == flows.shown(f"/flows/{flows.flow_id}/cycles?outcome=concluso")
    assert page["total"] == 1


def test_a_cycle_is_read_with_the_decisions_of_the_agent(flows: Flows) -> None:
    detail = flows.read("read_cycle", {"flow_id": flows.flow_id, "planned_at": "2026-11-12T10:00:00Z"})
    shown = flows.shown(f"/flows/{flows.flow_id}/cycles/2026-11-12T10:00:00Z")
    assert isinstance(shown, dict)

    assert detail == {name: value for name, value in shown.items() if name != "cost"}
    assert "decisione dell'agente" in detail["steps"]


def test_a_cycle_is_read_with_the_memory_the_agent_received_as_the_api_gives_it() -> None:
    flows = Flows()
    records = flows.cycles.platform.cycles.records
    entry = MemoryEntry(
        at("09:00"),
        "BTC",
        DecisionAction.OPEN,
        TradeSide.LONG,
        Decimal("95000.5"),
        "rottura",
        "sotto 94000",
        MemoryOutcome(Decimal("12.5"), realized=False, course="aperta da 1 ora"),
    )
    records[0] = replace(records[0], memory=(AssetMemory("BTC", (entry,)),))

    detail = flows.read("read_cycle", {"flow_id": flows.flow_id, "planned_at": "2026-11-12T10:00:00Z"})
    shown = flows.shown(f"/flows/{flows.flow_id}/cycles/2026-11-12T10:00:00Z")

    assert detail["memory"] == shown["memory"]
    assert detail["memory"][0]["entries"][0]["price"] == "95000.5"
    assert detail["memory"][0]["entries"][0]["outcome"]["course"] == "aperta da 1 ora"


def test_the_memory_of_a_flow_is_the_memory_of_the_api() -> None:
    flows = Flows()
    off = flows.read("read_flow_memory", {"flow_id": flows.flow_id})
    modified = flows.mcp.call_as(
        "anna", "modify_flow", {"flow_id": flows.flow_id, "modification": {"memory": {"active": True}}}
    )
    assert not modified.is_error, body_of(modified)

    on = flows.read("read_flow_memory", {"flow_id": flows.flow_id})

    assert off == {"active": False, "assets": []}
    assert on == flows.shown(f"/flows/{flows.flow_id}/memory")
    assert (on["active"], [asset["asset"] for asset in on["assets"]]) == (True, ["BTC"])


def test_the_tools_leave_the_motive_whole_and_remember_every_decision_as_the_api() -> None:
    flows = Flows()
    memory = {"active": True, "unlimited_text_length": True, "all_decisions": True}

    modified = flows.mcp.call_as("anna", "modify_flow", {"flow_id": flows.flow_id, "modification": {"memory": memory}})

    assert not modified.is_error, body_of(modified)
    changed = body_of(modified)["memory"]
    assert (changed["text_length"], changed["all_decisions"]) == (None, True)
    shown = flows.shown(f"/flows/{flows.flow_id}")
    assert isinstance(shown, dict)
    assert shown["memory"] == changed


def test_the_statistics_are_those_of_the_api(flows: Flows) -> None:
    statistics = flows.read("read_flow_statistics", {"flow_id": flows.flow_id})

    assert statistics == flows.shown(f"/flows/{flows.flow_id}/statistics")
    assert statistics["won"] == 1


def test_the_ranking_is_the_ranking_of_the_api(flows: Flows) -> None:
    assert flows.read("rank_flows")["flows"] == flows.shown("/flows/ranking")


def test_the_accounts_are_read_without_their_credentials(flows: Flows) -> None:
    (account,) = flows.read("list_accounts")["accounts"]
    (shown,) = flows.shown("/accounts")

    assert account == {
        name: shown[name] for name in ("id", "name", "exchange", "network", "allocated_capital", "currency")
    }
