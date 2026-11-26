"""ADR-memoria-del-flusso-con-riepilogo-e-altri-asset (R5.3.7): the summary and the other assets of the memory are off
by default and read off from a version saved before them; the summary lines are written by one type of the domain alone,
which only the memory of the flow builds, so the system prompt and every reading of the memory (API, MCP, dashboard)
show the lines as the agent receives them.
"""

import ast

from autotrading.domain.flows.flow_memory import FlowMemory
from tests.support.architecture import SourceModule, source_modules

SUMMARY_MODULE = "domain/flows/memory_summary.py"
SUMMARY_TYPE = "MemorySummary"
# The words of the line: only the type of the domain writes them.
LINE_WORDS = (" vinte, ", " perse, ")
BUILDERS = frozenset({SUMMARY_MODULE, "domain/flows/flow_memory.py"})

WRITING_ELSEWHERE = SourceModule.parse(
    "adapters/inbound/api/flows.py",
    """
def summary_line(asset, closed, won, lost):
    return f"{asset} short — oggi: {closed} chiuse, {won} vinte, {lost} perse"
""",
)
READING_THE_LINES = SourceModule.parse(
    "adapters/inbound/api/flows.py",
    """
def summary_lines(memory):
    return list(memory.summary)
""",
)
BUILDING_ELSEWHERE = SourceModule.parse(
    "application/flows/read_flow_memory.py",
    """
from autotrading.domain.flows.memory_summary import MemorySummary

def summary(closed, at):
    return MemorySummary(closed, at, 30, "USDC")
""",
)
BUILDING_THROUGH_THE_MEMORY = SourceModule.parse(
    "application/flows/remembered_decisions.py",
    """
def summary(memory, closed, at, currency):
    return memory.summary_of(closed, at, currency)
""",
)


def line_writers(modules: list[SourceModule]) -> list[str]:
    """Every module outside the type of the domain whose texts write the words of the summary line."""
    return [
        f"{module.path}:{node.lineno}: writes the summary line of the memory: only {SUMMARY_TYPE} writes it"
        for module in modules
        if module.path != SUMMARY_MODULE
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and any(w in node.value for w in LINE_WORDS)
    ]


def summary_builders(modules: list[SourceModule]) -> list[str]:
    """Every module but the memory of the flow that builds the summary itself."""
    return [
        f"{module.path}:{node.lineno}: builds {SUMMARY_TYPE}: the memory of the flow builds it (summary_of)"
        for module in modules
        if module.path not in BUILDERS
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == SUMMARY_TYPE
    ]


def test_adr_memoria_con_riepilogo_the_summary_and_the_other_assets_are_off_by_default() -> None:
    memory = FlowMemory(active=True)

    assert (memory.summary, memory.other_assets) == (False, False)


def test_adr_memoria_con_riepilogo_only_the_type_of_the_domain_writes_the_summary_line() -> None:
    assert line_writers([WRITING_ELSEWHERE]), "an adapter writes the summary line itself"
    assert not line_writers([READING_THE_LINES])
    assert line_writers(source_modules()) == []


def test_adr_memoria_con_riepilogo_only_the_memory_of_the_flow_builds_the_summary() -> None:
    assert summary_builders([BUILDING_ELSEWHERE]), "a use case builds the summary itself"
    assert not summary_builders([BUILDING_THROUGH_THE_MEMORY])
    assert summary_builders(source_modules()) == []
