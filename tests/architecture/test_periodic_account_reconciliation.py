"""ADR-riconciliazione-periodica-dei-conti-con-posizioni-aperte: ReconcileOpenAccountsUseCase of the flows context reads
the last reading saved, not the exchange, to skip an account without open positions or whose interval has not passed,
with the rule in the domain; it takes the lock of every flow of the account without waiting and reconciles with the
reconciliation of the cycle, which records the closings and tells the new cases; an error leaves the account for the
next check and pauses no flow; a periodic check of one minute for every tenant, in the apscheduler folder; the rule of
the flows context says the ledger is also written by the periodic check.
"""

import ast
import inspect
from datetime import timedelta
from pathlib import Path
from typing import get_type_hints

from autotrading import bootstrap
from autotrading.application.flows import ports as flow_ports
from autotrading.application.flows import reconcile_open_accounts, schedule_open_account_reconciliations
from autotrading.application.flows.reconcile_account_for_cycle import ReconcileAccountForCycleUseCase
from autotrading.application.flows.reconcile_open_accounts import OpenAccountReadings, ReconcileOpenAccountsUseCase
from autotrading.domain.flows.account_reconciliation import AccountReading

ROOT = Path(__file__).resolve().parents[2]
CONTEXT_RULE = ROOT / ".claude" / "rules" / "context-flows.md"
SCHEDULER_LIBRARY = "apscheduler"
# What would pause the flows from the check: the pause of the cycle, or the permanence of an error read here.
PAUSING = ("PauseAffectedFlows", "AutomaticPause", ".permanent")
RULE_SENTENCE = (
    "dalla riconciliazione del conto all'inizio e alla fine di ogni ciclo e dal controllo periodico dei conti con "
    "posizioni aperte (ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte)"
)


def _imported_roots(source: str) -> set[str]:
    tree = ast.parse(source)
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    return {module.split(".")[0] for module in imported}


def pausing_references(source: str) -> list[str]:
    return [name for name in PAUSING if name in source]


def test_adr_riconciliazione_periodica_the_due_rule_is_in_the_domain_on_the_saved_reading() -> None:
    assert callable(AccountReading.due_for_reconciliation)
    is_due = inspect.getsource(ReconcileOpenAccountsUseCase._is_due)
    assert "last_reading" in is_due
    assert "due_for_reconciliation" in is_due
    readings = get_type_hints(OpenAccountReadings)
    assert readings["readings"] is flow_ports.ReconciliationRepositoryPort
    assert readings["intervals"] is flow_ports.AccountReconciliationIntervalPort


def test_adr_riconciliazione_periodica_every_flow_of_the_account_is_held_and_the_cycle_reconciliation_runs() -> None:
    hints = get_type_hints(ReconcileOpenAccountsUseCase.__init__)
    held = inspect.getsource(ReconcileOpenAccountsUseCase._reconcile_unless_cycling)

    assert hints["lock"] is flow_ports.FlowLockPort
    assert hints["reconcile"] is ReconcileAccountForCycleUseCase
    assert "for flow in flows" in held
    assert "self._lock.hold(" in held
    assert "SqlAlchemyFlowLockAdapter(engine)" in inspect.getsource(bootstrap.reconcile_open_accounts)


def test_adr_riconciliazione_periodica_no_flow_is_paused_from_the_check() -> None:
    assert pausing_references(inspect.getsource(reconcile_open_accounts)) == []
    assert pausing_references(inspect.getsource(bootstrap.reconcile_open_accounts)) == []


def test_adr_riconciliazione_periodica_a_pause_from_the_check_is_found() -> None:
    assert pausing_references("PauseAffectedFlowsUseCase(flows, pause, notice)") == ["PauseAffectedFlows"]


def test_adr_riconciliazione_periodica_a_check_of_one_minute_in_the_apscheduler_folder() -> None:
    every = schedule_open_account_reconciliations.OPEN_ACCOUNT_RECONCILIATION_EVERY

    assert every == timedelta(minutes=1)
    for module in (reconcile_open_accounts, schedule_open_account_reconciliations):
        assert SCHEDULER_LIBRARY not in _imported_roots(inspect.getsource(module))
    assert "apscheduler_periodic_check_adapters()" in inspect.getsource(bootstrap.create_worker_application)
    assert "ScheduleOpenAccountReconciliationsUseCase(" in inspect.getsource(bootstrap.create_worker_application)


def test_adr_riconciliazione_periodica_a_scheduler_in_the_use_case_is_found() -> None:
    assert SCHEDULER_LIBRARY in _imported_roots("from apscheduler.triggers.interval import IntervalTrigger\n")


def test_adr_riconciliazione_periodica_the_rule_of_the_context_names_the_periodic_check() -> None:
    rule = " ".join(CONTEXT_RULE.read_text(encoding="utf-8").split())

    assert RULE_SENTENCE in rule
