"""ADR-memoria-del-flusso-dalle-decisioni-operative-precedenti (R5.3.4): the memory of the flow reaches the agent only
through the placeholder `{memory}` of the registry, which the default system prompt uses; the rule of the memory
(operative filter, order, limits, instant) lives in the domain, its reading behind a port of `flows`, and no other
module composes it beside the system prompt.
"""

import ast

from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT, PromptPlaceholder
from tests.support.architecture import SourceModule, source_modules

MEMORY = "memory"
PORTS = "application/flows/ports.py"
PAST_DECISIONS_PORT = "PastDecisionsPort"
RULE = "remembered_decisions"
RULE_MODULE = "application/flows/remembered_decisions.py"
# The only modules that may obtain the memory: the cycle composes it into the system prompt, the API shows it.
COMPOSERS = frozenset({"application/flows/compose_cycle_context.py", "application/flows/read_flow_memory.py"})

COMPOSING_ELSEWHERE = SourceModule.parse(
    "application/agent/compose_agent_context.py",
    """
from autotrading.application.flows.remembered_decisions import remembered_decisions

def context(decisions, flow_id, configuration, now):
    return remembered_decisions(decisions, flow_id, configuration, now, {})
""",
)
COMPOSING_IN_THE_CYCLE = SourceModule.parse(
    "application/flows/compose_cycle_context.py",
    """
from autotrading.application.flows.remembered_decisions import remembered_decisions

def context(decisions, flow_id, configuration, now):
    return remembered_decisions(decisions, flow_id, configuration, now, {})
""",
)
PORT_ELSEWHERE = SourceModule.parse(
    "application/agent/ports.py",
    """
from typing import Protocol

class PastDecisionsPort(Protocol):
    def past_decisions(self, flow_id, since): ...
""",
)
PORT_IN_FLOWS = SourceModule.parse(
    "application/flows/ports.py",
    """
from typing import Protocol

class PastDecisionsPort(Protocol):
    def past_decisions(self, flow_id, since): ...
""",
)


def composers(modules: list[SourceModule]) -> list[str]:
    """Every module outside the rule that obtains the memory, and is not one of the two that may."""
    return [
        f"{module.path}: obtains the memory of the flow outside the system prompt of the cycle and its consultation"
        for module in modules
        if module.path not in COMPOSERS | {RULE_MODULE}
        and any(
            isinstance(node, ast.ImportFrom) and any(alias.name == RULE for alias in node.names)
            for node in ast.walk(module.tree)
        )
    ]


def port_violations(modules: list[SourceModule]) -> list[str]:
    """The port of the past decisions declared anywhere but the ports of `flows`."""
    return [
        f"{module.path}: declares {PAST_DECISIONS_PORT} outside {PORTS}"
        for module in modules
        if module.path != PORTS
        for node in ast.walk(module.tree)
        if isinstance(node, ast.ClassDef) and node.name == PAST_DECISIONS_PORT
    ]


def test_adr_memoria_del_flusso_the_default_gives_the_memory_through_its_placeholder() -> None:
    assert MEMORY in {placeholder.value for placeholder in PromptPlaceholder}
    assert f"{{{MEMORY}}}" in DEFAULT_SYSTEM_PROMPT


def test_adr_memoria_del_flusso_the_memory_is_off_by_default_with_ten_decisions_and_thirty_days() -> None:
    memory = FlowMemory()

    assert (memory.active, memory.decisions, memory.days) == (False, 10, 30)


def test_adr_memoria_del_flusso_only_the_cycle_and_the_consultation_obtain_the_memory() -> None:
    assert composers([COMPOSING_ELSEWHERE]), "a module outside the two allowed obtains the memory"
    assert not composers([COMPOSING_IN_THE_CYCLE])
    assert composers(source_modules()) == []


def test_adr_memoria_del_flusso_the_past_decisions_are_read_behind_a_port_of_flows() -> None:
    assert port_violations([PORT_ELSEWHERE]), "the port declared outside the ports of flows"
    assert not port_violations([PORT_IN_FLOWS])
    found = [module for module in source_modules() if module.path == PORTS]
    assert any(isinstance(node, ast.ClassDef) and node.name == PAST_DECISIONS_PORT for node in ast.walk(found[0].tree))
    assert port_violations(source_modules()) == []
