"""ADR-movimenti-del-conto-nel-registro-con-cursore: the deposits, withdrawals and transfers of an account are rows of
the ledger, read with the executions from the cursor less an hour and written once; the reconciliation explains the
balance with those recorded after the previous reading; the activity of the account no longer reads nor carries them.
"""

import ast
import inspect
from dataclasses import fields
from pathlib import Path

from autotrading.adapters.inbound.api.account_activity import AccountActivityResponse
from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.hyperliquid.executions import HyperliquidAccountExecutionsAdapter
from autotrading.domain.flows import account_reconciliation
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.ledger import AccountLedger, ExecutionsWindow, LedgerKeys

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
MOVEMENTS = "movements"
LEDGER_OF_MOVEMENTS = "user_non_funding_ledger_updates"

# The shape of Bug 635: the balance explained by the movements the activity reads from the start of the account.
FROM_THE_ACTIVITY = """
def _explained(ledger, activity, since):
    return sum(movement.amount for movement in activity.movements if movement.moved_at > since)
"""
FROM_THE_LEDGER = """
def _explained(ledger, activity, since):
    return sum(movement.amount for movement in ledger.movements if since < movement.moved_at <= activity.read_at)
"""
ACTIVITY_READING_THE_LEDGER = """
def activity(self, reference):
    ledger = info.user_non_funding_ledger_updates(address, FROM_THE_START)
"""


def movements_read_from(source: str) -> set[str]:
    """The names whose movements the source reads."""
    return {
        node.value.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute) and node.attr == MOVEMENTS and isinstance(node.value, ast.Name)
    }


def calls(source: str, name: str) -> bool:
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == name
        for node in ast.walk(ast.parse(source))
    )


def method_source(owner: type, name: str) -> str:
    return inspect.cleandoc("\n" + inspect.getsource(getattr(owner, name)))


def migration_creating(table: str) -> str:
    """The source of the migration that creates the table, empty if none does."""
    return next(
        (
            source
            for migration in sorted(MIGRATIONS.glob("*.py"))
            if "op.create_table(" in (source := migration.read_text(encoding="utf-8")) and f'"{table}"' in source
        ),
        "",
    )


def test_adr_movimenti_del_conto_nel_registro_the_activity_carries_no_movements() -> None:
    assert MOVEMENTS not in {field.name for field in fields(AccountActivity)}
    assert MOVEMENTS not in AccountActivityResponse.model_fields


def test_adr_movimenti_del_conto_nel_registro_the_activity_no_longer_reads_the_ledger_of_movements() -> None:
    assert not calls(method_source(HyperliquidAccountActivityAdapter, "activity"), LEDGER_OF_MOVEMENTS)


def test_adr_movimenti_del_conto_nel_registro_the_movements_are_read_with_the_executions() -> None:
    assert calls(method_source(HyperliquidAccountExecutionsAdapter, "since"), LEDGER_OF_MOVEMENTS)
    assert {MOVEMENTS} <= {field.name for field in fields(ExecutionsWindow)}
    assert {MOVEMENTS} <= {field.name for field in fields(LedgerKeys)}
    assert {MOVEMENTS} <= {field.name for field in fields(AccountLedger)}


def test_adr_movimenti_del_conto_nel_registro_the_balance_is_explained_by_the_movements_of_the_ledger() -> None:
    assert movements_read_from(inspect.getsource(account_reconciliation._explained)) == {"ledger"}


def test_adr_movimenti_del_conto_nel_registro_a_reading_from_the_activity_is_found() -> None:
    assert movements_read_from(FROM_THE_ACTIVITY) == {"activity"}
    assert movements_read_from(FROM_THE_LEDGER) == {"ledger"}
    assert calls(ACTIVITY_READING_THE_LEDGER, LEDGER_OF_MOVEMENTS)


def test_adr_movimenti_del_conto_nel_registro_the_movements_have_their_table_once_per_tenant() -> None:
    migration = migration_creating("account_movements")

    assert 'name="account_movements_once"' in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY" in migration
    assert '"account_movements", ["tenant_id", "account_id", sa.text("moved_at DESC")]' in migration
    assert migration_creating("a_table_no_migration_creates") == ""
