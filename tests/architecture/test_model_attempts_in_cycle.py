"""ADR-tentativi-del-modello-registrati-nel-ciclo: a temporary failure of the model is asked again up to three times,
after 2, 8 and 30 seconds, and the attempts travel with the cost of the call: every carrier of the cost of the model
call, from the answer of the agent to the reading of the cycle, carries the attempts beside it.
"""

import ast

from autotrading.application.agent.ask_agent import RETRY_PAUSES_SECONDS
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

# The carriers of the cost of the model call of a cycle, in the order the cost travels: the answer of the agent, the
# error of the call, the port of the answer in flows, the journal and its failed call, the record, the reading.
COST_CARRIERS = (
    ("application/agent/ask_agent.py", "AgentAnswer"),
    ("application/agent/errors.py", "ModelUnavailableError"),
    ("application/flows/ports.py", "AgentReplyPort"),
    ("application/flows/ports.py", "CycleJournalPort"),
    ("application/flows/ports.py", "FailedModelCall"),
    ("domain/flows/cycle_record.py", "CycleRecord"),
    ("adapters/inbound/api/cycles.py", "CycleDetailResponse"),
)
ATTEMPTS = {"attempts", "model_attempts", "call_attempts"}


def cost_without_attempts(modules: list[SourceModule]) -> list[str]:
    """The carriers of the cost of the model call that do not name its attempts among their members."""
    return sorted(
        f"{module.path}:{node.name}"
        for module in modules
        for node in module.tree.body
        if isinstance(node, ast.ClassDef)
        and (module.path, node.name) in COST_CARRIERS
        and not _member_names(node) & ATTEMPTS
    )


def carriers_found(modules: list[SourceModule]) -> list[tuple[str, str]]:
    return [
        (module.path, node.name)
        for module in modules
        for node in module.tree.body
        if isinstance(node, ast.ClassDef) and (module.path, node.name) in COST_CARRIERS
    ]


def _member_names(node: ast.ClassDef) -> set[str]:
    """Fields, methods and the attributes the constructor sets."""
    names: set[str] = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.AnnAssign) and isinstance(inner.target, ast.Name):
            names.add(inner.target.id)
        if isinstance(inner, ast.FunctionDef):
            names.add(inner.name)
        if isinstance(inner, ast.Attribute) and isinstance(inner.ctx, ast.Store):
            names.add(inner.attr)
    return names


def test_adr_tentativi_del_modello_registrati_nel_ciclo_three_more_calls_after_2_8_and_30_seconds() -> None:
    assert RETRY_PAUSES_SECONDS == (2.0, 8.0, 30.0)


def test_adr_tentativi_del_modello_registrati_nel_ciclo_every_carrier_of_the_call_cost_carries_the_attempts() -> None:
    paths = {path for path, _carrier in COST_CARRIERS}
    modules = [module for module in source_modules(SOURCE_ROOT) if module.path in paths]

    assert sorted(carriers_found(modules)) == sorted(COST_CARRIERS)
    assert cost_without_attempts(modules) == []


def test_adr_tentativi_del_modello_registrati_nel_ciclo_a_cost_without_attempts_is_a_violation() -> None:
    reading = SourceModule.parse(
        "adapters/inbound/api/cycles.py",
        "class CycleDetailResponse(BaseModel):\n    cost: CallCostResponse | None\n    trigger: str\n",
    )
    journal = SourceModule.parse(
        "application/flows/ports.py",
        "class CycleJournalPort(Protocol):\n    def call_cost(self, decision: object) -> CallCost | None: ...\n",
    )

    assert cost_without_attempts([reading, journal]) == [
        "adapters/inbound/api/cycles.py:CycleDetailResponse",
        "application/flows/ports.py:CycleJournalPort",
    ]
