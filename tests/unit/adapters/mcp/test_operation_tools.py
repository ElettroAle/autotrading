"""Each operation tool runs the use case of the API for the tenant and the user of the token, with its rules."""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import pytest

from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.openings_suspension import OpeningsStatus, OpeningsSuspension
from tests.support.activity import a_fill
from tests.support.flow_cycles import FlowCycles, at
from tests.support.flows import OPENROUTER_MODEL
from tests.support.mcp_session import McpSession, body_of

CHOSEN_SOURCE = {"name": "indicatori", "adapters": [{"name": "Hyperliquid"}]}


class Flows:
    def __init__(self) -> None:
        self.cycles = FlowCycles()
        self.alfa = self.cycles.add_flow("anna", "alfa", assets=("BTC",))
        self.mcp = McpSession(self.cycles.platform)

    def flow(self, name: str) -> Flow:
        return self.cycles.flow(name)

    def call(self, tool: str, arguments: Mapping[str, object]) -> dict[str, Any]:
        result = self.mcp.call_as("anna", tool, arguments)
        assert not result.is_error, body_of(result)
        return body_of(result)

    def refusal(self, tool: str, arguments: Mapping[str, object]) -> dict[str, Any]:
        result = self.mcp.call_as("anna", tool, arguments)
        assert result.is_error, body_of(result)
        return body_of(result)

    def with_status(self, name: str, status: FlowStatus) -> str:
        flows = self.cycles.platform.flows.flows
        index = flows.index(self.flow(name))
        flows[index] = Flow(
            flows[index].id,
            flows[index].tenant_id,
            flows[index].account_id,
            flows[index].name,
            status,
            flows[index].configuration,
        )
        return str(flows[index].id.value)


@pytest.fixture
def flows() -> Flows:
    return Flows()


def test_a_flow_is_created_stopped_on_the_account_of_the_user(flows: Flows) -> None:
    creation = {
        "account_id": str(flows.alfa.assigned_account_id),
        "allocated_capital": "50",
        "name": "nuovo",
        "assets": ["SOL"],
        "model": OPENROUTER_MODEL,
        "max_leverage": 3,
        "max_margin_exposure_percent": "10",
    }

    created = flows.call("create_flow", {"flow": creation})

    assert (created["name"], created["status"], created["allocated_capital"]) == ("nuovo", "fermo", "50")
    assert flows.flow("nuovo").status is FlowStatus.STOPPED


def test_a_creation_the_rules_refuse_is_the_refusal_of_the_api(flows: Flows) -> None:
    creation = {"account_id": str(flows.alfa.assigned_account_id), "allocated_capital": "50", "name": "vuoto"}

    refusal = flows.refusal("create_flow", {"flow": creation})

    assert refusal["status"] == 422
    assert not [flow for flow in flows.cycles.platform.flows.flows if flow.name.value == "vuoto"]


def test_a_strategy_is_imported_as_a_draft(flows: Flows) -> None:
    strategy = {"model": OPENROUTER_MODEL, "max_leverage": 3, "max_margin_exposure_percent": "10"}

    draft = flows.call("import_flow_strategy", {"name": "importato", "strategy": strategy})

    assert (draft["name"], draft["status"], draft["account_id"]) == ("importato", "bozza", None)


def test_a_flow_is_duplicated_in_a_draft(flows: Flows) -> None:
    copy = flows.call("duplicate_flow", {"flow_id": str(flows.alfa.id.value)})

    assert (copy["status"], copy["name"]) == ("bozza", "alfa (copia)")
    assert copy["id"] != str(flows.alfa.id.value)


def test_a_modification_makes_a_new_version_with_the_parts_given(flows: Flows) -> None:
    flow_id = flows.with_status("alfa", FlowStatus.STOPPED)

    modified = flows.call(
        "modify_flow",
        {"flow_id": flow_id, "modification": {"instructions": "Prudente", "sources": [CHOSEN_SOURCE], "remove": []}},
    )

    assert (modified["version"], modified["instructions"]) == (2, "Prudente")
    assert [source["name"] for source in modified["sources"]] == ["indicatori"]


@pytest.mark.parametrize(
    ("tool", "status", "expected"),
    [
        ("start_flow", FlowStatus.STOPPED, FlowStatus.ACTIVE),
        ("pause_flow", FlowStatus.ACTIVE, FlowStatus.PAUSED),
        ("resume_flow", FlowStatus.PAUSED, FlowStatus.ACTIVE),
    ],
)
def test_the_status_changes_as_from_the_dashboard(
    flows: Flows, tool: str, status: FlowStatus, expected: FlowStatus
) -> None:
    flow_id = flows.with_status("alfa", status)

    changed = flows.call(tool, {"flow_id": flow_id})

    assert changed["status"] == expected.value
    assert flows.flow("alfa").status is expected


def test_a_stop_ends_the_flow_and_says_what_stayed_open(flows: Flows) -> None:
    stopped = flows.call("stop_flow", {"flow_id": str(flows.alfa.id.value)})

    assert stopped["flow"]["status"] == "fermo"
    assert stopped["left_open"] == []
    assert flows.flow("alfa").status is FlowStatus.STOPPED


def test_a_stopped_flow_is_archived(flows: Flows) -> None:
    flow_id = flows.with_status("alfa", FlowStatus.STOPPED)

    assert flows.call("archive_flow", {"flow_id": flow_id})["status"] == "archiviato"
    assert flows.flow("alfa").status is FlowStatus.ARCHIVED


def test_a_cycle_runs_now_and_is_answered_when_it_ends(flows: Flows) -> None:
    flows.cycles.clock.current = at("10:20")

    cycle = flows.call("run_cycle_now", {"flow_id": str(flows.alfa.id.value)})

    assert (cycle["trigger"], cycle["outcome"]) == ("on_demand", "concluso")


def test_the_openings_suspended_for_maximum_loss_resume(flows: Flows) -> None:
    store = flows.cycles.platform.flows
    store.openings[flows.alfa.id] = OpeningsStatus(OpeningsSuspension("perdita giornaliera", at("09:00")), None)

    resumed = flows.call("resume_flow_openings", {"flow_id": str(flows.alfa.id.value)})

    assert resumed == {"flow_id": str(flows.alfa.id.value)}
    assert store.openings[flows.alfa.id].suspension is None


def test_a_cash_out_frees_the_profits_of_the_flow(flows: Flows) -> None:
    profit = a_fill("BTC", None, realized_pnl=Decimal(18), size=Decimal(0))
    flows.cycles.platform.ledger.add(flows.alfa.assigned_account_id, flows.alfa.id, profit)

    cashed = flows.call("cash_out_profits", {"flow_id": str(flows.alfa.id.value), "capital": "80"})

    assert (cashed["capital"], cashed["left_open"]) == ("80", [])
    assert cashed["flow"]["allocated_capital"] == "80"


def test_a_cash_out_without_profits_is_the_conflict_of_the_api(flows: Flows) -> None:
    refusal = flows.refusal("cash_out_profits", {"flow_id": str(flows.alfa.id.value)})

    assert (refusal["status"], refusal["detail"]) == (409, "alfa non ha profitti da incassare")


def test_the_allocated_capital_changes_within_the_free_capital(flows: Flows) -> None:
    changed = flows.call("change_allocated_capital", {"flow_id": str(flows.alfa.id.value), "allocated_capital": "150"})

    assert changed["allocated_capital"] == "150"
    assert flows.flow("alfa").configuration.allocated_capital == 150
