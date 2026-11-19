"""ADR-controllo-giornaliero-delle-scadenze: the notifications read the keys through a port of their own and the flows
through theirs, both realized by the adapter of PostgreSQL; the check opens the alert, then records the threshold, then
tells it; the cycle pauses a flow with an expired key before its graph runs, through the existing pause and never
through an error declared permanent; the check runs every day at 06:00 UTC.
"""

import ast
import inspect
from datetime import UTC, time
from pathlib import Path

from autotrading.adapters.outbound.sqlalchemy.key_expiries import SqlAlchemyKeyExpiriesAdapter
from autotrading.application.flows.ports import FlowKeysPort
from autotrading.application.flows.run_cycle import RunCycleUseCase
from autotrading.application.notifications.check_key_expiries import CheckKeyExpiriesUseCase
from autotrading.application.notifications.ports import ExpiringKeysPort
from autotrading.domain.notifications.expiring_key import DAILY_CHECK_AT
from tests.support.architecture import SOURCE_ROOT

ORDER_OF_A_THRESHOLD = ("self._alerts.open", "self._notices.record", "self._notifier.execute")

# The notice leaves before the threshold is recorded: two checks together would both tell it.
TOLD_BEFORE_RECORDED = """
class CheckKeyExpiriesUseCase:
    def _check(self, key, today):
        alert_id = self._alerts.open(AlertCause.key_expiry(key, today))
        self._notifier.execute(Notification.key_expiry(alert_id.value, key, today))
        self._notices.record(key.notice_on(today))
"""
RECORDED_BEFORE_TOLD = """
class CheckKeyExpiriesUseCase:
    def _check(self, key, today):
        notice = key.notice_on(today)
        alert_id = self._alerts.open(AlertCause.key_expiry(key, today))
        if not self._notices.record(notice):
            return
        self._notifier.execute(Notification.key_expiry(alert_id.value, key, today))
"""
# The graph runs first: the cycle would ask the model with a key already expired.
GRAPH_FIRST = """
class RunCycleUseCase:
    def execute(self, command):
        outcome = self._graph.run(cycle, self._guards.clock.now())
        if self._guards.expired_keys.execute(PauseFlowsOnExpiredKeysCommand(command.flow_id)):
            return None
"""
KEYS_FIRST = """
class RunCycleUseCase:
    def execute(self, command):
        if self._guards.expired_keys.execute(PauseFlowsOnExpiredKeysCommand(command.flow_id)):
            return None
        outcome = self._graph.run(cycle, self._guards.clock.now())
"""


def calls_in_order(source: str, method: str) -> list[str]:
    """The calls of the method, in the order of their lines."""
    tree = ast.parse(source)
    [found] = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == method]
    calls = sorted(
        (node.lineno, node.col_offset, ast.unparse(node.func)) for node in ast.walk(found) if isinstance(node, ast.Call)
    )
    return [name for _, _, name in calls]


def tells_a_threshold_once(source: str) -> bool:
    calls = [call for call in calls_in_order(source, "_check") if call in ORDER_OF_A_THRESHOLD]
    return tuple(calls) == ORDER_OF_A_THRESHOLD


def pauses_before_the_graph(source: str) -> bool:
    calls = calls_in_order(source, "execute")
    keys, graph = "self._guards.expired_keys.execute", "self._graph.run"
    return keys in calls and graph in calls and calls.index(keys) < calls.index(graph)


def test_adr_controllo_giornaliero_the_rules_tell_the_right_order_from_the_wrong_one() -> None:
    assert not tells_a_threshold_once(TOLD_BEFORE_RECORDED)
    assert tells_a_threshold_once(RECORDED_BEFORE_TOLD)
    assert not pauses_before_the_graph(GRAPH_FIRST)
    assert pauses_before_the_graph(KEYS_FIRST)


def test_adr_controllo_giornaliero_the_check_opens_the_alert_then_records_the_threshold_then_tells_it() -> None:
    assert tells_a_threshold_once(inspect.getsource(CheckKeyExpiriesUseCase))


def test_adr_controllo_giornaliero_the_cycle_pauses_a_flow_with_an_expired_key_before_its_graph_runs() -> None:
    assert pauses_before_the_graph(inspect.getsource(RunCycleUseCase))


def test_adr_controllo_giornaliero_each_context_reads_the_keys_through_its_port_and_one_adapter_realizes_both() -> None:
    for port in (ExpiringKeysPort, FlowKeysPort):
        members = {name for name in vars(port) if not name.startswith("_")}
        assert members <= set(vars(SqlAlchemyKeyExpiriesAdapter)), port.__name__


def test_adr_controllo_giornaliero_no_error_of_an_expired_key_declares_itself_permanent() -> None:
    declaring = [
        f"{path.relative_to(SOURCE_ROOT)}:{node.name}"
        for path in Path(SOURCE_ROOT).rglob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.ClassDef)
        and "Expir" in node.name
        and any(
            isinstance(statement, ast.Assign | ast.AnnAssign) and "permanent" in ast.unparse(statement)
            for statement in node.body
        )
    ]
    assert declaring == []


def test_adr_controllo_giornaliero_the_check_runs_every_day_at_six_in_utc() -> None:
    assert time(6, 0, tzinfo=UTC) == DAILY_CHECK_AT
