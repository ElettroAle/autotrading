"""ADR-inversione-in-due-passi-nel-ciclo: the agent reverses an open position with the action «inverti»; the risk
check approves the closing with the reason of a reversal and keeps the opening pending; the graph of the cycle checks
and sends that opening in a node of its own, after the orders of the cycle and before the ledger, on the account
reconciled after the closing.
"""

import ast
import inspect
import json
from decimal import Decimal
from pathlib import Path
from typing import get_type_hints

from autotrading.application.flows import cycle_graph
from autotrading.application.flows import ports as flow_ports
from autotrading.application.flows.check_risk import CheckRiskUseCase
from autotrading.application.flows.reverse_cycle_positions import ReverseCyclePositionsUseCase
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.agent.decision import Decision, TradeAction
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.recorded_decision import DecisionAction
from autotrading.domain.flows.risk_outcome import ApprovedClose, BlockedDecision
from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT
from autotrading.domain.flows.trade_intent import ReverseIntent, TradeIntent
from autotrading.domain.flows.trade_side import TradeSide

GRAPH = Path(inspect.getfile(cycle_graph))


def parameters(function: object) -> list[str]:
    assert callable(function)
    return list(inspect.signature(function).parameters)


def edges_of(source: str) -> set[tuple[str, str]]:
    """The edges the graph declares, each conditional edge with every node it may lead to."""
    edges: set[tuple[str, str]] = set()
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        texts = [argument for argument in ast.walk(node) if isinstance(argument, ast.Constant)]
        names = [text.value for text in texts if isinstance(text.value, str)]
        if node.func.attr in {"add_edge", "add_conditional_edges"} and names:
            edges |= {(names[0], target) for target in names[1:]}
    return edges


def test_adr_inversione_in_due_passi_the_reversal_is_an_action_of_the_agent_in_the_rigid_schema() -> None:
    decision = json.loads(json.dumps(DECISIONS_FORMAT.schema))["properties"]["decisioni"]["items"]

    assert TradeAction.REVERSE.value == "inverti"
    assert "inverti" in decision["properties"]["azione"]["enum"]
    assert {action.value for action in DecisionAction} == {action.value for action in TradeAction}
    assert parameters(Decision.intent_with)[-1] == "reversing"
    assert "- inverti chiude per intero la posizione aperta" in DEFAULT_SYSTEM_PROMPT


def test_adr_inversione_in_due_passi_the_risk_check_closes_with_the_reason_and_keeps_the_opening_pending() -> None:
    reversal = ReverseIntent("BTC", Decimal("0.1"), 3, 70)
    closing = ApprovedClose("BTC", reversal.opening(TradeSide.LONG))

    assert ReverseIntent in TradeIntent.__value__.__args__
    assert closing.reason is CloseReason.REVERSAL
    assert closing.reopening is not None
    assert closing.reopening.side is TradeSide.SHORT
    assert BlockedDecision.without_reversible_position("BTC").reason.endswith("nessuna posizione da invertire")
    assert CloseReason.REVERSAL.value == "inversione"


def test_adr_inversione_in_due_passi_the_opening_is_sent_in_its_own_node_after_the_orders_and_before_the_ledger() -> (
    None
):
    edges = edges_of(GRAPH.read_text("utf-8"))

    assert {target for source, target in edges if source == "execute"} == {"reverse", "update_ledger"}
    assert {target for source, target in edges if source == "reverse"} == {"update_ledger"}
    assert {source for source, target in edges if target == "reverse"} == {"execute"}
    assert get_type_hints(cycle_graph.CycleSteps)["reversal"].__origin__ is flow_ports.ReversalPort


def test_adr_inversione_in_due_passi_a_reversal_outside_its_place_in_the_graph_is_found() -> None:
    violating = 'graph.add_edge("execute", "update_ledger")\ngraph.add_edge("update_ledger", "reverse")'

    edges = edges_of(violating)

    assert {target for source, target in edges if source == "execute"} == {"update_ledger"}
    assert {source for source, target in edges if target == "reverse"} == {"update_ledger"}


def test_adr_inversione_in_due_passi_the_opening_is_checked_on_the_account_reconciled_after_the_closing() -> None:
    hints = get_type_hints(ReverseCyclePositionsUseCase.__init__)

    assert hints["record_executions"] is flow_ports.AccountExecutionsRecorderPort
    assert hints["read_flow"] is flow_ports.CycleFlowReaderPort
    assert hints["check_risk"] is CheckRiskUseCase
    assert hints["loss_guard"] is flow_ports.FlowLossGuardPort
    assert hints["send_orders"].__origin__ is flow_ports.OrderPort
