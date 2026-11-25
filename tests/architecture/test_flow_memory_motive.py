"""ADR-memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni (R5.3.5): the answer of the model carries a
motive the reading does not require; the memory cuts the motive at 160 characters and remembers only openings, closings
and reversals unless the user says otherwise; which actions the memory remembers is a rule of the domain alone, which
the port of the past decisions receives, so no module outside the domain that reads the past decisions names an action.
"""

import ast

from autotrading.domain.agent.agent_response import MOTIVE, AgentResponse
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.recorded_decision import DecisionAction
from tests.support.architecture import SourceModule, source_modules

PORTS = "application/flows/ports.py"
PAST_DECISIONS_PORT = "PastDecisionsPort"
READING = "past_decisions"
ACTIONS = "actions"
ACTION_TYPE = DecisionAction.__name__

NAMING_ACTIONS = SourceModule.parse(
    "adapters/outbound/sqlalchemy/past_decisions.py",
    """
OPERATIVE = frozenset({DecisionAction.OPEN, DecisionAction.CLOSE})

class SqlAlchemyPastDecisionsAdapter:
    def past_decisions(self, flow_id, window):
        return [row for row in rows if row.action in OPERATIVE]
""",
)
RECEIVING_ACTIONS = SourceModule.parse(
    "adapters/outbound/sqlalchemy/past_decisions.py",
    """
class SqlAlchemyPastDecisionsAdapter:
    def past_decisions(self, flow_id, window, actions):
        return [row for row in rows if row.action in actions]
""",
)


def actions_named_outside_the_domain(modules: list[SourceModule]) -> list[str]:
    """Every module outside the domain that reads the past decisions and names an action of its own."""
    return [
        f"{module.path}:{node.lineno}: names {ACTION_TYPE}.{node.attr} beside the past decisions: the memory gives the"
        f" actions it remembers to the port"
        for module in modules
        if module.layer != "domain" and _reads_past_decisions(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == ACTION_TYPE
    ]


def _reads_past_decisions(module: SourceModule) -> bool:
    return any(
        isinstance(node, ast.FunctionDef | ast.Attribute)
        and (node.name if isinstance(node, ast.FunctionDef) else node.attr) == READING
        for node in ast.walk(module.tree)
    )


def port_parameters(modules: list[SourceModule]) -> list[str]:
    [ports] = [module for module in modules if module.path == PORTS]
    [port] = [
        node for node in ast.walk(ports.tree) if isinstance(node, ast.ClassDef) and node.name == PAST_DECISIONS_PORT
    ]
    [reading] = [node for node in port.body if isinstance(node, ast.FunctionDef) and node.name == READING]
    return [argument.arg for argument in reading.args.args]


def test_adr_memoria_con_motivo_the_answer_carries_a_motive_the_reading_does_not_require() -> None:
    decision = DECISIONS_FORMAT.schema["properties"]
    assert isinstance(decision, dict)
    entry = decision["decisioni"]["items"]["properties"]

    assert entry[MOTIVE] == {"type": ["string", "null"]}
    without_motive = '{"decisioni": [{"asset": "BTC", "azione": "mantieni", "confidenza": 50, "ragionamento": "x"}]}'
    assert AgentResponse.read(without_motive, ("BTC",)).decisions[0].motive is None


def test_adr_memoria_con_motivo_the_memory_cuts_at_160_and_remembers_openings_closings_and_reversals() -> None:
    memory = FlowMemory()

    assert (memory.text_length, memory.all_decisions) == (160, False)
    assert memory.remembered_actions == {DecisionAction.OPEN, DecisionAction.CLOSE, DecisionAction.REVERSE}


def test_adr_memoria_con_motivo_the_port_of_the_past_decisions_receives_the_actions_from_the_memory() -> None:
    assert ACTIONS in port_parameters(source_modules())


def test_adr_memoria_con_motivo_no_module_beside_the_past_decisions_names_the_actions_outside_the_domain() -> None:
    assert actions_named_outside_the_domain([NAMING_ACTIONS]), "an adapter names the actions the memory remembers"
    assert not actions_named_outside_the_domain([RECEIVING_ACTIONS])
    assert actions_named_outside_the_domain(source_modules()) == []
