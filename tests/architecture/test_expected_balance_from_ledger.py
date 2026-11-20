"""ADR-saldo-atteso-dalle-righe-del-registro-dopo-la-lettura-precedente: the reconciliation explains the balance with
every row of the ledger after the previous reading, whoever recorded it, read through FlowLedgerPort; the rows just
recorded stay the base of what is new. The rows of an account by instant are served by an index.
"""

import ast
import inspect
from pathlib import Path
from typing import get_type_hints
from uuid import UUID

from autotrading.application.flows import reconcile_account
from autotrading.application.flows.ports import FlowLedgerPort
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.domain.flows import account_reconciliation
from autotrading.domain.flows.account_reconciliation import AccountReconciliation
from autotrading.domain.flows.ledger import AccountLedger

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
READ_FROM_THE_LEDGER = "recorded_after"

# The shape of Bug 633: the balance compared with the rows the reconciliation has just recorded.
RECORDED_ONLY = """
def of(cls, account_id, flows_of_account, activity, previous, recorded, threshold_percent):
    comparison = _comparison(previous, recorded, activity)
"""
FROM_THE_LEDGER = """
def of(cls, account_id, flows_of_account, activity, previous, recorded, ledger_since_previous, threshold_percent):
    comparison = _comparison(previous, ledger_since_previous, activity)
"""
WITHOUT_THE_LEDGER = """
class ReconcileAccountUseCase:
    def execute(self, command):
        recorded = self._record_executions.execute(command)
"""
WITH_THE_LEDGER = """
class ReconcileAccountUseCase:
    def _ledger_since(self, account_id, previous):
        return self._ledger.recorded_after(account_id, previous.read_at)
"""


def compared_with(source: str) -> list[str]:
    """The names the comparison of the balance receives."""
    return [
        argument.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_comparison"
        for argument in node.args
        if isinstance(argument, ast.Name)
    ]


def reads_the_ledger(source: str) -> bool:
    return any(
        isinstance(node, ast.Attribute) and node.attr == READ_FROM_THE_LEDGER for node in ast.walk(ast.parse(source))
    )


def index_created(name: str) -> str:
    """The source of the migration that creates the index, empty if none does."""
    return next(
        (
            source
            for migration in sorted(MIGRATIONS.glob("*.py"))
            if f'"{name}"' in (source := migration.read_text(encoding="utf-8"))
        ),
        "",
    )


def test_adr_saldo_atteso_dalle_righe_del_registro_the_ledger_gives_the_rows_after_a_moment() -> None:
    hints = get_type_hints(FlowLedgerPort.recorded_after)

    assert hints == {"account_id": UUID, "since": hints["since"], "return": AccountLedger}


def test_adr_saldo_atteso_dalle_righe_del_registro_the_reconciliation_reads_them_from_the_ledger() -> None:
    assert get_type_hints(ReconcileAccountUseCase.__init__)["ledger"] is FlowLedgerPort
    assert reads_the_ledger(inspect.getsource(reconcile_account))


def test_adr_saldo_atteso_dalle_righe_del_registro_the_balance_is_compared_with_the_rows_of_the_ledger() -> None:
    assert get_type_hints(AccountReconciliation.of)["ledger_since_previous"] is AccountLedger
    assert compared_with(inspect.getsource(account_reconciliation)) == ["previous", "ledger_since_previous", "activity"]


def test_adr_saldo_atteso_dalle_righe_del_registro_a_comparison_on_the_rows_just_recorded_is_found() -> None:
    assert "recorded" in compared_with(RECORDED_ONLY)
    assert "recorded" not in compared_with(FROM_THE_LEDGER)
    assert not reads_the_ledger(WITHOUT_THE_LEDGER)
    assert reads_the_ledger(WITH_THE_LEDGER)


def test_adr_saldo_atteso_dalle_righe_del_registro_the_rows_of_an_account_by_instant_have_an_index() -> None:
    fills = index_created("account_fills_of_account")
    funding = index_created("account_funding_of_account")

    assert '"account_fills", ["tenant_id", "account_id", sa.text("executed_at DESC")]' in fills
    assert '"account_funding", ["tenant_id", "account_id", sa.text("paid_at DESC")]' in funding
    assert index_created("an_index_no_migration_creates") == ""
