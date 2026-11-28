"""ADR-riconciliazione-periodica-dei-conti-con-posizioni-aperte: ReconcileOpenAccountsUseCase of the flows context reads
the last reading saved, not the exchange, to skip an account without open positions or whose interval has not passed,
with the rule in the domain; it tries the exclusion of the reconciliation of the account without waiting, never the
exclusion of the flows, and reconciles with ReconcileAccountUseCase telling the new cases as the cycle; the
reconciliation of the cycle waits for the same exclusion; the exclusion is a port of flows realized in the sqlalchemy
folder with a PostgreSQL advisory lock whose key space is apart from the one of the cycles; an error leaves the account
for the next check and pauses no flow; a periodic check of one minute for every tenant, in the apscheduler folder; the
rule of the flows context says the ledger is also written by the periodic check.
"""

import ast
import inspect
from datetime import timedelta
from pathlib import Path
from typing import get_type_hints
from uuid import uuid4

from autotrading import bootstrap
from autotrading.adapters.outbound.sqlalchemy import account_reconciliation_locks, scheduling
from autotrading.application.flows import ports as flow_ports
from autotrading.application.flows import reconcile_open_accounts, schedule_open_account_reconciliations
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import (
    AccountReconciliation,
    AccountReconciliationExclusion,
    ReconcileAccountForCycleUseCase,
)
from autotrading.application.flows.reconcile_open_accounts import OpenAccountReadings, ReconcileOpenAccountsUseCase
from autotrading.domain.flows.account_reconciliation import AccountReading

ROOT = Path(__file__).resolve().parents[2]
CONTEXT_RULE = ROOT / ".claude" / "rules" / "context-flows.md"
SCHEDULER_LIBRARY = "apscheduler"
# What would pause the flows from the check: the pause of the cycle, or the permanence of an error read here.
PAUSING = ("PauseAffectedFlows", "AutomaticPause", ".permanent")
# The exclusion of the flows, which would skip a cycle planned while the check runs.
FLOW_EXCLUSION = ("FlowLockPort", "SqlAlchemyFlowLockAdapter")
RULE_SENTENCE = (
    "dalla riconciliazione del conto all'inizio e alla fine di ogni ciclo e dal controllo periodico dei conti con "
    "posizioni aperte (ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte)"
)


def _imported_roots(source: str) -> set[str]:
    tree = ast.parse(source)
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    return {module.split(".")[0] for module in imported}


def holds_the_flows(source: str) -> list[str]:
    return [name for name in FLOW_EXCLUSION if name in source]


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


def test_adr_riconciliazione_periodica_the_check_tries_the_account_and_never_holds_the_flows() -> None:
    hints = get_type_hints(ReconcileOpenAccountsUseCase.__init__)
    held = inspect.getsource(ReconcileOpenAccountsUseCase._reconcile_unless_running)
    check = inspect.getsource(reconcile_open_accounts) + inspect.getsource(bootstrap.reconcile_open_accounts)

    assert hints["lock"] is flow_ports.AccountReconciliationLockPort
    assert get_type_hints(AccountReconciliation)["reconcile_account"] is ReconcileAccountUseCase
    assert "self._lock.try_hold(account_id)" in held
    assert holds_the_flows(check) == []
    assert "SqlAlchemyAccountReconciliationLockAdapter(engine)" in inspect.getsource(bootstrap.reconcile_open_accounts)


def test_adr_riconciliazione_periodica_holding_the_flows_is_found() -> None:
    assert holds_the_flows("lock: FlowLockPort") == ["FlowLockPort"]


def test_adr_riconciliazione_periodica_the_cycle_waits_for_the_same_exclusion() -> None:
    hints = get_type_hints(AccountReconciliationExclusion)
    execute = inspect.getsource(ReconcileAccountForCycleUseCase.execute)

    assert hints["lock"] is flow_ports.AccountReconciliationLockPort
    assert "self._exclusion.lock.hold(account_id)" in execute
    assert "AccountReconciliationExclusion(flows, SqlAlchemyAccountReconciliationLockAdapter(engine))" in (
        inspect.getsource(bootstrap)
    )


def test_adr_riconciliazione_periodica_the_exclusion_is_an_advisory_lock_apart_from_the_cycles() -> None:
    adapter = account_reconciliation_locks.SqlAlchemyAccountReconciliationLockAdapter
    source = inspect.getsource(account_reconciliation_locks)

    assert callable(adapter.hold)
    assert callable(adapter.try_hold)
    assert "pg_advisory_lock" in source
    assert "pg_try_advisory_lock" in source
    # A pair of 32-bit numbers: a key space PostgreSQL keeps apart from the single 64-bit keys of the cycles.
    assert len(account_reconciliation_locks.account_reconciliation_key(uuid4())) == 2
    assert isinstance(scheduling.lock_key(uuid4()), int)


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
