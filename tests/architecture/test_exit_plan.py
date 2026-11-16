"""ADR-piano-di-uscita-nella-decisione-dell-agente and ADR-piano-di-uscita-nella-dashboard: the exit plan of an opening
is a value object of the domain, declared by the rigid schema of the answer, checked by the risk check on the market
price of the exchange, kept per flow and asset behind a port under row level security, and shown by the dashboard with
the shared table and label-value list on the fields of the generated client.
"""

import dataclasses
import inspect
import json
import re
from pathlib import Path
from typing import get_type_hints

from autotrading.adapters.inbound.api.flow_state import FlowPositionResponse
from autotrading.application.flows import ports
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.agent.decision import TradeOpening
from autotrading.domain.agent.exit_plan import ExitPlan
from autotrading.domain.flows.exit_plan import ExitPlan as FlowExitPlan
from autotrading.domain.flows.risk_check import AssetLimits
from autotrading.domain.flows.risk_outcome import AdjustmentKind, ApprovedOpening
from autotrading.domain.flows.trade_intent import OpenIntent

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY / "migrations" / "versions"
DASHBOARD = REPOSITORY / "dashboard" / "src"
PLAN_FIELDS = ["target", "stop", "invalidation"]
PLAN_KEYS = {"obiettivo", "stop", "invalidazione"}
API_PLAN_FIELDS = ("target_price", "stop_price", "invalidation")


def field_names(cls: type) -> list[str]:
    return [field.name for field in dataclasses.fields(cls)]


def test_adr_piano_di_uscita_the_plan_is_a_value_object_of_the_decision_and_of_the_opening() -> None:
    assert field_names(ExitPlan) == PLAN_FIELDS
    assert field_names(FlowExitPlan) == PLAN_FIELDS
    assert get_type_hints(TradeOpening)["exit_plan"] is ExitPlan
    assert get_type_hints(OpenIntent)["exit_plan"] is FlowExitPlan
    assert get_type_hints(ApprovedOpening)["exit_plan"] is FlowExitPlan


def test_adr_piano_di_uscita_the_rigid_schema_wants_every_key_of_the_plan_nullable() -> None:
    entry = json.loads(json.dumps(DECISIONS_FORMAT.schema))["properties"]["decisioni"]["items"]

    assert set(entry["required"]) >= PLAN_KEYS
    assert all("null" in entry["properties"][key]["type"] for key in PLAN_KEYS)


def test_adr_piano_di_uscita_the_risk_check_reads_the_market_price_and_notes_the_discarded_levels() -> None:
    assert "market_price" in field_names(AssetLimits)
    assert AdjustmentKind.EXIT_PLAN.value == "piano di uscita"


def test_adr_piano_di_uscita_the_plan_in_force_is_kept_behind_a_port_of_the_flows() -> None:
    port = ports.ExitPlanRepositoryPort

    assert [name for name, _ in inspect.getmembers(port, inspect.isfunction) if not name.startswith("_")] == [
        "current",
        "remove",
        "save",
    ]


def test_adr_piano_di_uscita_the_table_of_the_plans_belongs_to_a_tenant_under_row_level_security() -> None:
    migration = next(MIGRATIONS.glob("*_flow_exit_plans.py")).read_text(encoding="utf-8")

    assert '"tenant_id"' in migration
    assert "ALTER TABLE flow_exit_plans FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY flow_exit_plans_of_tenant" in migration


def test_adr_piano_di_uscita_nella_dashboard_the_api_and_its_generated_client_carry_the_plan() -> None:
    schema = (DASHBOARD / "lib" / "api-schema.d.ts").read_text(encoding="utf-8")
    position = re.search(r"FlowPositionResponse: \{(.*?)\n        \};", schema, re.DOTALL)

    assert set(FlowPositionResponse.model_fields) >= set(API_PLAN_FIELDS)
    assert position is not None
    assert all(f"{name}: string | null;" in position.group(1) for name in API_PLAN_FIELDS)


def test_adr_piano_di_uscita_nella_dashboard_the_plan_grows_the_shared_components() -> None:
    positions = (DASHBOARD / "features" / "flow-positions" / "components" / "open-positions.tsx").read_text(
        encoding="utf-8"
    )
    decision = (DASHBOARD / "features" / "cycles" / "components" / "step-document.tsx").read_text(encoding="utf-8")

    assert "from '@/components/ui/data-table'" in positions
    assert "rowDetail=" in positions
    assert "from '@/components/ui/details-list'" in decision
    assert not list(DASHBOARD.rglob("*exit-plan*"))
