"""ADR-periodo-di-6-ore-e-dall-inizio: the periods are the durations of the domain and one list in the dashboard, the
shared selector, in the same order; the fake API of the dashboard accepts the same ones. The whole life keeps `all` in
the address and is named «Dall'inizio», never «Tutta la vita».
"""

import re
from pathlib import Path

from autotrading.domain.flows.statistics_period import StatisticsPeriodKind

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard" / "src"
SELECTOR = DASHBOARD / "components" / "ui" / "period-selector" / "use-period.ts"
FAKE_API = DASHBOARD / "testing" / "mocks" / "flow-statistics.ts"
DOMAIN_PERIODS = [kind.value for kind in StatisticsPeriodKind]
SELECTOR_ENTRY = re.compile(r"\{\s*kind:\s*'(?P<kind>[^']+)',\s*label:\s*(?P<quote>['\"])(?P<label>.+?)(?P=quote)\s*\}")
FAKE_NAMES = re.compile(r"const PERIOD_NAMES = \[(?P<names>[^\]]*)\]")
OLD_NAME = "Tutta la vita"

CONFORMING_SELECTOR = """
export const PERIODS = [
  { kind: '30m', label: '30 minuti' },
  { kind: '1h', label: '1 ora' },
  { kind: '6h', label: '6 ore' },
  { kind: '12h', label: '12 ore' },
  { kind: '24h', label: '24 ore' },
  { kind: '7d', label: '7 giorni' },
  { kind: '30d', label: '30 giorni' },
  { kind: 'all', label: "Dall'inizio" },
  { kind: 'range', label: 'Intervallo' },
] as const;
"""
VIOLATING_SELECTOR = """
export const PERIODS = [
  { kind: '30m', label: '30 minuti' },
  { kind: '1h', label: '1 ora' },
  { kind: '12h', label: '12 ore' },
  { kind: '24h', label: '24 ore' },
  { kind: '7d', label: '7 giorni' },
  { kind: '30d', label: '30 giorni' },
  { kind: 'all', label: 'Tutta la vita' },
  { kind: 'range', label: 'Intervallo' },
] as const;
"""


def selector_violations(selector: str) -> list[str]:
    """What keeps the shared selector from offering the periods of the domain, the whole life named «Dall'inizio»."""
    entries = {match["kind"]: match["label"] for match in SELECTOR_ENTRY.finditer(selector)}
    found = []
    if list(entries) != DOMAIN_PERIODS:
        found.append(f"the selector offers {list(entries)}, the domain {DOMAIN_PERIODS}")
    if entries.get("all") != "Dall'inizio":
        found.append(f"the whole life is named {entries.get('all')!r}")
    return found


def fake_api_periods(fake_api: str) -> list[str]:
    match = FAKE_NAMES.search(fake_api)
    return [] if match is None else re.findall(r"'([^']+)'", match["names"])


def files_with_the_old_name(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.suffix in {".ts", ".tsx"} and OLD_NAME in path.read_text(encoding="utf-8")
    )


def test_adr_periodo_di_6_ore_e_dall_inizio_the_selector_offers_the_periods_of_the_domain() -> None:
    assert selector_violations(SELECTOR.read_text(encoding="utf-8")) == []


def test_adr_periodo_di_6_ore_e_dall_inizio_the_fake_api_accepts_the_periods_of_the_domain() -> None:
    assert fake_api_periods(FAKE_API.read_text(encoding="utf-8")) == DOMAIN_PERIODS


def test_adr_periodo_di_6_ore_e_dall_inizio_no_page_names_the_whole_life_the_old_way() -> None:
    assert files_with_the_old_name(DASHBOARD) == []


def test_adr_periodo_di_6_ore_e_dall_inizio_a_selector_without_6_hours_and_with_the_old_name_is_found() -> None:
    assert selector_violations(VIOLATING_SELECTOR) == [
        f"the selector offers {['30m', '1h', '12h', '24h', '7d', '30d', 'all', 'range']}, the domain {DOMAIN_PERIODS}",
        "the whole life is named 'Tutta la vita'",
    ]
    assert selector_violations(CONFORMING_SELECTOR) == []


def test_adr_periodo_di_6_ore_e_dall_inizio_a_file_with_the_old_name_is_found(tmp_path: Path) -> None:
    (tmp_path / "menu.tsx").write_text("const label = 'Tutta la vita';\n", encoding="utf-8")
    (tmp_path / "other.ts").write_text('const label = "Dall\'inizio";\n', encoding="utf-8")

    assert files_with_the_old_name(tmp_path) == ["menu.tsx"]
