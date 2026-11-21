"""ADR-riparazione-delle-chiusure-attribuite-a-un-altro-flusso: one Alembic migration of data brings the closings of
the flows recorded without their flow back to the flow they closed, with their executions and the totals of the flows
touched, recognising them from the data alone: no identifier of a flow or of a row is written in it, and its downgrade
does not restore the wrong attribution.
"""

import ast
import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
REPAIR = "repaired_flow_closings"
UUID_TEXT = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
CHANGED_TABLES = ("orders", "account_fills", "flow_totals", "flow_position_totals")

# The repair as it would be written for the data of one installation only.
WITH_THE_IDS_OF_DEV = """
def upgrade():
    op.execute("UPDATE account_fills SET flow_id = '6b1c6c48-3d38-4e66-8a27-175e074c49a2' WHERE asset = 'BTC'")
"""
FROM_THE_DATA = """
def upgrade():
    op.execute("UPDATE account_fills SET flow_id = repaired.flow_id FROM repaired WHERE order_id = repaired.order_id")
"""
RESTORING = """
def downgrade():
    op.execute("UPDATE account_fills SET flow_id = NULL")
"""
NOT_RESTORING = """
def downgrade():
    # The wrong attribution is not restored.
    pass
"""


def repair_migration() -> str:
    (source,) = [
        text for path in sorted(MIGRATIONS.glob("*.py")) if REPAIR in (text := path.read_text(encoding="utf-8"))
    ]
    return source


def identifiers_written(source: str) -> list[str]:
    """The identifiers written as text in the source of a migration."""
    return UUID_TEXT.findall(source)


def downgrade_restores(source: str) -> bool:
    """Whether the downgrade of the migration does anything at all."""
    (downgrade,) = [
        node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "downgrade"
    ]
    return not all(isinstance(statement, ast.Pass) for statement in downgrade.body)


def test_adr_riparazione_delle_chiusure_one_migration_repairs_orders_executions_and_totals() -> None:
    source = repair_migration()

    for table in CHANGED_TABLES:
        assert re.search(rf"(UPDATE|INSERT INTO) {table}\b", source), table
        assert f'"{table}"' in source, table
    assert "ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY" in source
    assert "ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in source


def test_adr_riparazione_delle_chiusure_the_migration_writes_no_identifier() -> None:
    assert identifiers_written(repair_migration()) == []


def test_adr_riparazione_delle_chiusure_an_identifier_written_in_a_migration_is_found() -> None:
    assert identifiers_written(WITH_THE_IDS_OF_DEV) == ["6b1c6c48-3d38-4e66-8a27-175e074c49a2"]
    assert identifiers_written(FROM_THE_DATA) == []


def test_adr_riparazione_delle_chiusure_the_downgrade_does_not_restore_the_wrong_attribution() -> None:
    assert not downgrade_restores(repair_migration())


def test_adr_riparazione_delle_chiusure_a_downgrade_that_restores_is_found() -> None:
    assert downgrade_restores(RESTORING)
    assert not downgrade_restores(NOT_RESTORING)
