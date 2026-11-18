"""ADR-prossima-esecuzione-nel-riepilogo-del-flusso: the next cycle of a flow has one rule, the schedule the domain
plans for the flow (`Flow.planned_schedule`), shared by the list of the flows and the summary of the page of the flow;
the summary of the API carries it and the dashboard only shows it, without computing an instant of its own.
"""

import ast
from pathlib import Path

from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

CANONICAL = "domain/flows/flow.py"
PLANNED = "planned"
SCHEDULE = "CycleSchedule"
DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard"
SUMMARY = DASHBOARD / "src" / "features" / "flows" / "components" / "results-summary.tsx"
FLOW_RESULTS = DASHBOARD / "src" / "features" / "flows" / "components" / "flow-results.tsx"
API_SCHEMA = DASHBOARD / "src" / "lib" / "api-schema.d.ts"

# The summary as a use case could have planned it on its own, beside the list: a second copy of the rule.
PLANNED_IN_A_USE_CASE = """
def _next_cycle_of(flow, anchor, now):
    interval = timedelta(minutes=flow.configuration.cycle_interval.minutes)
    schedule = CycleSchedule.planned(flow.status.runs_cycles, anchor, interval)
    return None if schedule is None else schedule.next_after(now)
"""
PLANNED_BY_THE_FLOW = """
def _next_cycle_of(flow, anchor, now):
    schedule = flow.planned_schedule(anchor)
    return None if schedule is None else schedule.next_after(now)
"""
# The dashboard adding the interval to the last cycle: an instant the API did not give.
COMPUTED_IN_THE_DASHBOARD = """
<Value term="Prossima esecuzione prevista">
  {formatInstant(new Date(Date.parse(lastCycle) + cycleMinutes * MINUTE).toISOString())}
</Value>
"""
SHOWN_FROM_THE_API = """
<Value term="Prossima esecuzione prevista">{formatInstant(nextCycleAt)}</Value>
"""


def plannings_outside_the_flow(module: SourceModule) -> list[str]:
    """Every call of `CycleSchedule.planned` of the module, as path and line, unless the module is the flow."""
    if module.path == CANONICAL:
        return []
    return [
        f"src/autotrading/{module.path}:{node.lineno}"
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == PLANNED
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == SCHEDULE
    ]


def instants_computed_in(component: str) -> list[str]:
    """What, in a component of the dashboard, computes the next cycle instead of showing the instant of the API."""
    found = []
    if "Prossima esecuzione prevista" not in component:
        found.append("no «Prossima esecuzione prevista»")
    found.extend(word for word in ("cycleMinutes", "Date.parse", "MINUTE") if word in component)
    return found


def test_adr_prossima_esecuzione_the_schedule_is_planned_only_by_the_flow() -> None:
    found = [location for module in source_modules(SOURCE_ROOT) for location in plannings_outside_the_flow(module)]

    assert found == [], f"la pianificazione dei cicli si legge da Flow.planned_schedule ({CANONICAL}): {found}"


def test_adr_prossima_esecuzione_a_schedule_planned_beside_the_flow_is_found() -> None:
    assert plannings_outside_the_flow(SourceModule.parse("application/flows/read_next_cycle.py", PLANNED_IN_A_USE_CASE))
    assert (
        plannings_outside_the_flow(SourceModule.parse("application/flows/read_next_cycle.py", PLANNED_BY_THE_FLOW))
        == []
    )


def test_adr_prossima_esecuzione_the_summary_of_the_api_and_its_client_carry_the_next_cycle() -> None:
    schema = API_SCHEMA.read_text(encoding="utf-8")
    results = schema[schema.index("FlowResultsResponse: {") :]

    assert "next_cycle_at: string | null;" in results[: results.index("};")]
    assert "summary.next_cycle_at" in FLOW_RESULTS.read_text(encoding="utf-8")


def test_adr_prossima_esecuzione_the_dashboard_shows_the_instant_of_the_api() -> None:
    assert instants_computed_in(SUMMARY.read_text(encoding="utf-8")) == []


def test_adr_prossima_esecuzione_an_instant_computed_in_the_dashboard_is_found() -> None:
    assert instants_computed_in(COMPUTED_IN_THE_DASHBOARD) == ["cycleMinutes", "Date.parse", "MINUTE"]
    assert instants_computed_in(SHOWN_FROM_THE_API) == []
