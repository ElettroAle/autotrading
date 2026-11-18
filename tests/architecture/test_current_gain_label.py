"""ADR-nomi-e-istanti-dei-guadagni (Bug 612): the gain read now is «Guadagno attuale» wherever the dashboard and the
requirements show it; «Guadagno totale» names it nowhere, and no note goes below the values.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "dashboard"
SUMMARY = DASHBOARD / "src" / "features" / "flows" / "components" / "results-summary.tsx"
OLD_NAME = "guadagno totale"
NEW_NAME = "Guadagno attuale"
SEARCHED = (
    (DASHBOARD / "src", "*.ts*"),
    (DASHBOARD / "e2e", "*.ts"),
    (ROOT / "specs", "*.feature"),
)
# The requirement that renamed the gain quotes the old name on purpose, to say what it replaces.
RENAMING_REQUIREMENT = "R6.4.8-prossima-esecuzione-nella-panoramica.feature"

OLD_LABEL = '<Gain term="Guadagno totale" amount={summary.total_gain} />'
NEW_LABEL = '<Gain term="Guadagno attuale" amount={summary.total_gain} />'


def old_names_in(text: str) -> int:
    return text.lower().count(OLD_NAME)


def files_with_the_old_name() -> list[str]:
    return [
        path.relative_to(ROOT).as_posix()
        for folder, pattern in SEARCHED
        for path in sorted(folder.rglob(pattern))
        if "node_modules" not in path.parts
        and path.name != RENAMING_REQUIREMENT
        and old_names_in(path.read_text(encoding="utf-8"))
    ]


def test_adr_nomi_e_istanti_dei_guadagni_the_gain_read_now_is_the_current_gain() -> None:
    assert files_with_the_old_name() == []
    assert f'term="{NEW_NAME}"' in SUMMARY.read_text(encoding="utf-8")


def test_adr_nomi_e_istanti_dei_guadagni_the_old_name_is_found() -> None:
    assert old_names_in(OLD_LABEL) == 1
    assert old_names_in(NEW_LABEL) == 0
