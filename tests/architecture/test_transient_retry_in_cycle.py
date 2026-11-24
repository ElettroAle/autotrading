"""ADR-errori-temporanei-ritentati-in-ogni-passo-del-ciclo: a temporary error of a step of the cycle is retried in the
same cycle by one policy in application, five times after 5, 15, 30, 60 and 120 seconds since
ADR-ritentativo-del-ciclo-entro-meta-dell-intervallo.

The graph calls the port of every step through the policy, but the sources, which stay absent instead, the model, which
keeps its own attempts, and the orders and the reversals, which the orders context sends again one by one so that an
order executed is never sent twice. The orders context sends an order only through the sending that asks the exchange
for it by its client order id before sending it again. The retry policy of LangGraph never retries a node.
"""

import ast
import inspect

from autotrading.application.flows.transient_retry import RETRY_PAUSES_SECONDS
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase
from autotrading.application.orders.ports import SendingRetryPort
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

CYCLE_GRAPH = "application/flows/cycle_graph.py"
FLOW_ORDERS = "application/orders/execute_flow_orders.py"
RETRIED_PORTS = frozenset({"start", "context", "risk", "end"})
PORTS_WITH_THEIR_OWN_ATTEMPTS = frozenset({"sources", "agent", "orders", "reversal"})
RETRY_CALL = "_retried"
SENDING = "OrderSending"
LANGGRAPH_RETRY = frozenset({"RetryPolicy", "retry_policy"})


def step_calls(module: SourceModule) -> dict[str, bool]:
    """Every port of a step the graph calls, and whether the call goes through the retry policy of the cycle."""
    retried = {
        id(inner)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and _called_name(node) == RETRY_CALL
        for inner in ast.walk(node)
    }
    return {
        port: id(node) in retried
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and (port := _step_port(node)) is not None
    }


def direct_sendings(module: SourceModule) -> list[int]:
    """The lines where the orders of a flow are sent once, without the sending that asks for them before again."""
    return [
        node.lineno
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and _called_name(node) in {"send_order", "place_market_order"}
    ]


def sends_through_the_retried_sending(module: SourceModule) -> bool:
    return any(isinstance(node, ast.Call) and _called_name(node) == SENDING for node in ast.walk(module.tree))


def langgraph_retries(modules: list[SourceModule]) -> list[str]:
    return sorted(
        f"{module.path}:{node.lineno}"
        for module in modules
        for node in ast.walk(module.tree)
        if (isinstance(node, ast.Name) and node.id in LANGGRAPH_RETRY)
        or (isinstance(node, ast.keyword) and node.arg in LANGGRAPH_RETRY)
        or (isinstance(node, ast.alias) and node.name in LANGGRAPH_RETRY)
    )


def _step_port(call: ast.Call) -> str | None:
    """The port behind `self._steps.<port>.execute(...)`."""
    function = call.func
    if not (isinstance(function, ast.Attribute) and function.attr in {"execute", "call_all"}):
        return None
    owner = function.value
    if not (isinstance(owner, ast.Attribute) and isinstance(owner.value, ast.Attribute)):
        return None
    if owner.value.attr != "_steps" or owner.attr == "calls":
        return None
    return owner.attr


def _called_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _module(path: str) -> SourceModule:
    (module,) = [module for module in source_modules(SOURCE_ROOT) if module.path == path]
    return module


def test_adr_ritentativo_del_ciclo_entro_meta_dell_intervallo_five_more_calls_after_5_15_30_60_and_120_seconds() -> (
    None
):
    assert RETRY_PAUSES_SECONDS == (5.0, 15.0, 30.0, 60.0, 120.0)


def test_adr_errori_temporanei_ritentati_in_ogni_passo_del_ciclo_every_other_step_retried() -> None:
    calls = step_calls(_module(CYCLE_GRAPH))

    assert set(calls) == RETRIED_PORTS | PORTS_WITH_THEIR_OWN_ATTEMPTS
    assert {port for port, retried in calls.items() if retried} == RETRIED_PORTS


def test_adr_errori_temporanei_ritentati_in_ogni_passo_del_ciclo_step_not_retried_violates() -> None:
    graph = SourceModule.parse(
        CYCLE_GRAPH,
        "class CycleGraph:\n"
        "    def _load_state(self, cycle, failed):\n"
        "        return self._steps.start.execute(cycle.flow_id, cycle.schedule.anchor)\n"
        "    def _execute(self, cycle, state, failed):\n"
        "        return self._retried(STEP, lambda: self._steps.orders.execute(cycle.flow_id), failed)\n",
    )

    assert step_calls(graph) == {"start": False, "orders": True}


def test_adr_errori_temporanei_ritentati_in_ogni_passo_del_ciclo_order_looked_up_first() -> None:
    module = _module(FLOW_ORDERS)

    assert inspect.signature(ExecuteFlowOrdersUseCase.__init__).parameters["retry"].annotation is SendingRetryPort
    assert direct_sendings(module) == []
    assert sends_through_the_retried_sending(module)


def test_adr_errori_temporanei_ritentati_in_ogni_passo_del_ciclo_blind_resend_violates() -> None:
    blind = SourceModule.parse(
        FLOW_ORDERS,
        "class ExecuteFlowOrdersUseCase:\n"
        "    def _opened(self, sending, request):\n"
        "        return self._retry.run(lambda: send_order(sending.exchange, sending.access, request), self._told)\n",
    )

    assert direct_sendings(blind) == [3]
    assert not sends_through_the_retried_sending(blind)


def test_adr_errori_temporanei_ritentati_in_ogni_passo_del_ciclo_langgraph_never_retries_a_node() -> None:
    assert langgraph_retries(source_modules(SOURCE_ROOT)) == []


def test_adr_errori_temporanei_ritentati_in_ogni_passo_del_ciclo_node_retry_violates() -> None:
    graph = SourceModule.parse(
        CYCLE_GRAPH,
        "from langgraph.types import RetryPolicy\n"
        "graph.add_node('execute', node, retry_policy=RetryPolicy(max_attempts=3))\n",
    )

    assert langgraph_retries([graph]) == [f"{CYCLE_GRAPH}:1", f"{CYCLE_GRAPH}:2", f"{CYCLE_GRAPH}:2"]
