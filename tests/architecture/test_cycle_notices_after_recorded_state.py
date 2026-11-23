"""ADR-notifiche-del-ciclo-dopo-lo-stato-registrato: the notices the steps of a cycle give are held by decorators of
their own ports in `process_memory/`, created for every cycle, and `RunCycleUseCase` releases them as its last step,
so the state of the flow at their bottom is the one after what they tell (Bug 729).
"""

import ast
from typing import get_type_hints

from autotrading.adapters.outbound.process_memory import cycle_notices
from autotrading.application.flows.ports import CycleNoticesPort
from autotrading.application.flows.run_cycle import RunCycleUseCase
from tests.support.architecture import SOURCE_ROOT, Rule, SourceModule, violations_of

FOLDER = "adapters/outbound/process_memory"
COMPOSITION = "process_memory_cycle_notices_adapters"
WORKER_CYCLE = "cycle_of"
CYCLE = "cycle_for"
# Every notice a step of the cycle gives, with the decorator that holds it until the cycle releases them.
HELD_NOTICES = {
    "NotifyPositionOpenedUseCase": "ProcessMemoryPositionOpenedNoticeAdapter",
    "NotifyOrderRejectedUseCase": "ProcessMemoryOrderRejectedNoticeAdapter",
    "NotifyPositionClosedUseCase": "ProcessMemoryPositionClosedNoticeAdapter",
    "NotifyOpeningsSuspendedUseCase": "ProcessMemoryOpeningsSuspendedNoticeAdapter",
    "NotifyOpeningReducedUseCase": "ProcessMemoryOpeningReducedNoticeAdapter",
    "NotifyOpeningBlockedUseCase": "ProcessMemoryOpeningBlockedNoticeAdapter",
}

NOTICE_TOLD_AT_ONCE = f"""
def {WORKER_CYCLE}(engine):
    def {CYCLE}(tenant_id):
        notices = {COMPOSITION}()
        follow = FlowOrderFollowers(NotifyOrderRejectedUseCase(notify_flow), opened, closing)
        return RunCycleUseCase(graph, guards, equity, notices)
"""
NOTICE_HELD = f"""
def {WORKER_CYCLE}(engine):
    def {CYCLE}(tenant_id):
        notices = {COMPOSITION}()
        rejected = ProcessMemoryOrderRejectedNoticeAdapter(NotifyOrderRejectedUseCase(notify_flow), notices)
        return RunCycleUseCase(graph, guards, equity, notices)
"""
NOTICES_SHARED_BY_THE_CYCLES = f"""
def {WORKER_CYCLE}(engine):
    notices = {COMPOSITION}()
    def {CYCLE}(tenant_id):
        rejected = ProcessMemoryOrderRejectedNoticeAdapter(NotifyOrderRejectedUseCase(notify_flow), notices)
        return RunCycleUseCase(graph, guards, equity, notices)
"""
DECORATOR_RECEIVING_ANOTHER_PORT = """
from autotrading.application.orders.ports import OrderRejectedNoticePort, PositionOpenedNoticePort

class ProcessMemoryOrderRejectedNoticeAdapter(OrderRejectedNoticePort):
    def __init__(self, decorated: OrderRejectedNoticePort, opened: PositionOpenedNoticePort) -> None: ...
"""


def _function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    return next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name), None)


def _called(node: ast.AST) -> str | None:
    return node.func.id if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) else None


def notices_told_at_once(source: str) -> list[str]:
    """Every notice of a step the cycle of the worker builds outside the decorator that holds it, as name and line."""
    cycle = _function(ast.parse(source), CYCLE)
    assert cycle is not None, f"{CYCLE} non trovato"
    held = {
        id(argument)
        for node in ast.walk(cycle)
        if _called(node) in HELD_NOTICES.values() and isinstance(node, ast.Call)
        for argument in node.args[:1]
        if HELD_NOTICES.get(_called(argument) or "") == _called(node)
    }
    return [
        f"{_called(node)}:{node.lineno}"
        for node in ast.walk(cycle)
        if _called(node) in HELD_NOTICES and isinstance(node, ast.Call) and id(node) not in held
    ]


def notices_created_for_every_cycle(source: str) -> bool:
    """The notices are created inside the cycle, never once for the cycles of every tenant."""
    worker_cycle = _function(ast.parse(source), WORKER_CYCLE)
    cycle = _function(ast.parse(source), CYCLE)
    assert worker_cycle is not None
    assert cycle is not None
    outside = [node for node in worker_cycle.body if not isinstance(node, ast.FunctionDef)]
    return COMPOSITION in ast.unparse(cycle) and all(COMPOSITION not in ast.unparse(node) for node in outside)


def _bootstrap() -> str:
    return (SOURCE_ROOT / "bootstrap.py").read_text(encoding="utf-8")


def test_adr_notifiche_del_ciclo_dopo_lo_stato_registrato_every_notice_of_a_step_is_held() -> None:
    found = notices_told_at_once(_bootstrap())

    assert found == [], (
        f"le notifiche dei passi del ciclo partono dopo lo stato registrato: avvolgi ciascuna nel suo decorator di "
        f"{FOLDER} ({found})"
    )


def test_adr_notifiche_del_ciclo_dopo_lo_stato_registrato_a_notice_told_at_once_is_found() -> None:
    assert notices_told_at_once(NOTICE_TOLD_AT_ONCE) == ["NotifyOrderRejectedUseCase:5"]
    assert notices_told_at_once(NOTICE_HELD) == []


def test_adr_notifiche_del_ciclo_dopo_lo_stato_registrato_the_notices_are_created_for_every_cycle() -> None:
    assert notices_created_for_every_cycle(_bootstrap())


def test_adr_notifiche_del_ciclo_dopo_lo_stato_registrato_notices_shared_by_the_cycles_are_found() -> None:
    assert notices_created_for_every_cycle(NOTICE_HELD)
    assert not notices_created_for_every_cycle(NOTICES_SHARED_BY_THE_CYCLES)


def test_adr_notifiche_del_ciclo_dopo_lo_stato_registrato_the_cycle_releases_the_notices() -> None:
    assert get_type_hints(RunCycleUseCase.__init__)["notices"] is CycleNoticesPort
    assert CycleNoticesPort in cycle_notices.ProcessMemoryCycleNoticesAdapter.__bases__


def test_adr_notifiche_del_ciclo_dopo_lo_stato_registrato_every_hold_is_a_decorator_of_its_port() -> None:
    path = f"{FOLDER}/cycle_notices.py"
    module = SourceModule.parse(path, (SOURCE_ROOT / path).read_text(encoding="utf-8"))
    decorators = [getattr(cycle_notices, name) for name in HELD_NOTICES.values()]

    assert [violation.rule for violation in violations_of(module)] == []
    assert all(len(decorator.__bases__) == 1 for decorator in decorators)
    assert [
        violation.rule for violation in violations_of(SourceModule.parse(path, DECORATOR_RECEIVING_ANOTHER_PORT))
    ] == [Rule.ADAPTERS_DO_NOT_ORCHESTRATE]
