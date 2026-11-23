"""ADR-ritentativo-del-ciclo-entro-meta-dell-intervallo: a new attempt of the cycle starts only if, after its wait, the
clock is still within half the interval of the flow from the planned instant of the cycle.

The graph sets the limit of the one retry of the cycle before any node runs, from the schedule and the planned instant
of the cycle; the retry reads the instant from the clock port of the cycle. The model keeps its own attempts.
"""

import ast
import inspect

from autotrading.application.agent.ask_agent import RETRY_PAUSES_SECONDS as MODEL_PAUSES_SECONDS
from autotrading.application.flows.ports import ClockPort
from autotrading.application.flows.transient_retry import TransientRetry
from autotrading.domain.flows.cycle_schedule import RETRY_WINDOW_SHARE
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

CYCLE_GRAPH = "application/flows/cycle_graph.py"
LIMIT = "limit_to"
LIMIT_OF_THE_SCHEDULE = "retry_limit"


def limits_before_the_nodes(module: SourceModule) -> bool:
    """Whether `CycleGraph.run` limits the retry to the schedule of the cycle before anything else."""
    run = _run_of_the_graph(module)
    if run is None:
        return False
    first = _first_statement(run)
    return isinstance(first, ast.Expr) and _limits_to_the_schedule(first.value)


def _run_of_the_graph(module: SourceModule) -> ast.FunctionDef | None:
    for node in module.tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "CycleGraph":
            for inner in node.body:
                if isinstance(inner, ast.FunctionDef) and inner.name == "run":
                    return inner
    return None


def _first_statement(function: ast.FunctionDef) -> ast.stmt:
    body = function.body
    has_docstring = isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
    return body[1] if has_docstring else body[0]


def _limits_to_the_schedule(call: ast.expr) -> bool:
    """`self._retry.limit_to(cycle.schedule.retry_limit(...))`."""
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == LIMIT):
        return False
    (argument,) = call.args
    return (
        isinstance(argument, ast.Call)
        and isinstance(argument.func, ast.Attribute)
        and argument.func.attr == LIMIT_OF_THE_SCHEDULE
    )


def _module(path: str) -> SourceModule:
    (module,) = [module for module in source_modules(SOURCE_ROOT) if module.path == path]
    return module


def test_adr_ritentativo_del_ciclo_entro_meta_dell_intervallo_window_is_half_the_interval() -> None:
    assert RETRY_WINDOW_SHARE == 2


def test_adr_ritentativo_del_ciclo_entro_meta_dell_intervallo_retry_reads_the_clock_of_the_cycle() -> None:
    assert inspect.signature(TransientRetry.__init__).parameters["clock"].annotation is ClockPort


def test_adr_ritentativo_del_ciclo_entro_meta_dell_intervallo_graph_limits_the_retry_before_the_nodes() -> None:
    assert limits_before_the_nodes(_module(CYCLE_GRAPH))


def test_adr_ritentativo_del_ciclo_entro_meta_dell_intervallo_graph_without_the_limit_first_violates() -> None:
    late = SourceModule.parse(
        CYCLE_GRAPH,
        "class CycleGraph:\n"
        "    def run(self, cycle, started_at):\n"
        '        """Runs the cycle."""\n'
        "        thread = self._checkpoints.thread(cycle.flow_id, cycle.planned_at)\n"
        "        self._retry.limit_to(cycle.schedule.retry_limit(cycle.planned_at))\n",
    )
    from_the_start = SourceModule.parse(
        CYCLE_GRAPH,
        "class CycleGraph:\n    def run(self, cycle, started_at):\n        self._retry.limit_to(started_at)\n",
    )
    conforming = SourceModule.parse(
        CYCLE_GRAPH,
        "class CycleGraph:\n"
        "    def run(self, cycle, started_at):\n"
        '        """Runs the cycle."""\n'
        "        self._retry.limit_to(cycle.schedule.retry_limit(cycle.planned_at))\n",
    )

    assert not limits_before_the_nodes(late)
    assert not limits_before_the_nodes(from_the_start)
    assert limits_before_the_nodes(conforming)


def test_adr_ritentativo_del_ciclo_entro_meta_dell_intervallo_model_keeps_its_own_attempts() -> None:
    assert MODEL_PAUSES_SECONDS == (2.0, 8.0, 30.0)
