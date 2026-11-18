"""ADR-movimenti-non-spiegati-nel-riquadro-del-conto: the record of what no flow explains belongs to the account. The
box of the account shows it right under its reconciliation, with the shared table and its shared filters, never a
table or filters of its own; the record is read from the port of the reconciliations, one page at a time.
"""

import inspect
import re
from pathlib import Path

from autotrading.application.flows.ports import ReconciliationRepositoryPort

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard" / "src"
COMPONENTS = DASHBOARD / "features" / "accounts" / "components"
CARD = COMPONENTS / "account-card.tsx"
MOVEMENTS = COMPONENTS / "unattributable-movements.tsx"
SECTIONS = re.compile(r"<(ReconciliationStatus|UnattributableMovements|AccountActions) ")

OWN_TABLE = """
export const UnattributableMovements = ({ account }) => (
  <section><table><tbody>{rows.map((row) => <tr><td>{row.kind}</td></tr>)}</tbody></table></section>
);
"""
SHARED_TABLE = """
export const UnattributableMovements = ({ account }) => (
  <section><DataTable label="Movimenti non spiegati" rows={rows} filtering={{ filters, total, countOf }} /></section>
);
"""


def card_violations(card: str) -> list[str]:
    """What keeps the record from coming right under the reconciliation of the account."""
    order = SECTIONS.findall(card)
    if order[:2] != ["ReconciliationStatus", "UnattributableMovements"]:
        return [f"the box shows {order}, not the record right under the reconciliation"]
    return []


def section_violations(section: str) -> list[str]:
    """What keeps the record on the shared table with its shared filters."""
    found = []
    if "<table" in section:
        found.append("a table of its own")
    if "<DataTable" not in section:
        found.append("no shared table")
    if "filtering=" not in section:
        found.append("no shared filters")
    return found


def test_adr_movimenti_non_spiegati_nel_riquadro_del_conto_the_box_shows_the_record_under_the_reconciliation() -> None:
    assert card_violations(CARD.read_text(encoding="utf-8")) == []
    assert section_violations(MOVEMENTS.read_text(encoding="utf-8")) == []


def test_adr_movimenti_non_spiegati_nel_riquadro_del_conto_a_record_elsewhere_or_on_its_own_table_is_found() -> None:
    assert card_violations("<ReconciliationStatus account={a} /><AccountActions account={a} />") == [
        "the box shows ['ReconciliationStatus', 'AccountActions'], not the record right under the reconciliation"
    ]
    assert section_violations(OWN_TABLE) == ["a table of its own", "no shared table", "no shared filters"]
    assert section_violations(SHARED_TABLE) == []


def test_adr_movimenti_non_spiegati_nel_riquadro_del_conto_the_record_is_read_by_pages_from_the_reconciliations() -> (
    None
):
    parameters = list(inspect.signature(ReconciliationRepositoryPort.unattributable_of).parameters)

    assert parameters == ["self", "account_id", "criteria", "cursor"]
