"""ADR-rendimento-del-periodo-nelle-statistiche (Bug 689): the statistics of a flow carry the return of their period,
computed by `FlowReturn`, the one computation of the return (ADR rendimento-composto-tra-le-variazioni-di-capitale),
so with the whole life they show the return of the summary; the panel of the dashboard shows it with the shared colour
of gains and losses.
"""

import ast
from pathlib import Path

from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

STATISTICS = "domain/flows/flow_statistics.py"
STATISTICS_CLASS = "FlowStatistics"
RETURN_FIELD = "return_percent"
CANONICAL_NAME = "FlowReturn"
COMPUTED_APART = f"il rendimento delle statistiche non si calcola con {CANONICAL_NAME}"
PANEL = (
    SOURCE_ROOT.parents[1] / "dashboard" / "src" / "features" / "flow-statistics" / "components" / "flow-statistics.tsx"
)
PANEL_LABEL = 'label="Rendimento"'
SHARED_TONE = "gainTone("

# The return computed in the statistics on their own, from the first and the last value: a change of the capital in
# the period would move it, and it would differ from the return of the summary.
OWN_COMPUTATION = """
class FlowStatistics:
    return_percent: Decimal | None

    @classmethod
    def of(cls, positions, cost, values):
        first, last = values[0].equity, values[-1].equity
        return cls(return_percent=(last - first) / first * PERCENT)
"""
WITHOUT_RETURN = """
class FlowStatistics:
    won: int
"""
THROUGH_THE_CANONICAL = """
class FlowStatistics:
    return_percent: Decimal | None

    @classmethod
    def of(cls, positions, cost, values, changes):
        return cls(return_percent=FlowReturn.over(values, changes).percent)
"""


def _declares_the_return(module: SourceModule) -> bool:
    return any(
        isinstance(node, ast.ClassDef)
        and node.name == STATISTICS_CLASS
        and any(
            isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name) and field.target.id == RETURN_FIELD
            for field in node.body
        )
        for node in ast.walk(module.tree)
    )


def _uses_the_canonical_computation(module: SourceModule) -> bool:
    return any(isinstance(node, ast.Name) and node.id == CANONICAL_NAME for node in ast.walk(module.tree))


def statistics_return_findings(module: SourceModule) -> list[str]:
    """What keeps the statistics of the module from carrying the return of `FlowReturn`, as reasons."""
    findings: list[str] = []
    if not _declares_the_return(module):
        findings.append(f"{STATISTICS_CLASS} non ha {RETURN_FIELD}")
    if not _uses_the_canonical_computation(module):
        findings.append(COMPUTED_APART)
    return findings


def panel_findings(text: str) -> list[str]:
    """What keeps the panel from showing the return with the shared colour of gains and losses, as reasons."""
    findings: list[str] = []
    if PANEL_LABEL not in text:
        findings.append("il pannello delle statistiche non mostra «Rendimento»")
    if SHARED_TONE not in text:
        findings.append("il pannello delle statistiche non usa il colore condiviso di guadagno e perdita")
    return findings


def test_adr_rendimento_del_periodo_the_statistics_carry_the_return_of_flow_return() -> None:
    [module] = [module for module in source_modules(SOURCE_ROOT) if module.path == STATISTICS]

    assert statistics_return_findings(module) == [], f"src/autotrading/{STATISTICS}"


def test_adr_rendimento_del_periodo_the_panel_shows_the_return_with_the_shared_colour() -> None:
    assert panel_findings(Path(PANEL).read_text(encoding="utf-8")) == []


def test_adr_rendimento_del_periodo_a_return_computed_apart_is_found() -> None:
    module = SourceModule.parse(STATISTICS, OWN_COMPUTATION)

    assert statistics_return_findings(module) == [COMPUTED_APART]


def test_adr_rendimento_del_periodo_statistics_without_return_are_found() -> None:
    module = SourceModule.parse(STATISTICS, WITHOUT_RETURN)

    assert f"{STATISTICS_CLASS} non ha {RETURN_FIELD}" in statistics_return_findings(module)


def test_adr_rendimento_del_periodo_the_return_of_flow_return_is_not_found() -> None:
    module = SourceModule.parse(STATISTICS, THROUGH_THE_CANONICAL)

    assert statistics_return_findings(module) == []


def test_adr_rendimento_del_periodo_a_panel_without_the_return_is_found() -> None:
    assert len(panel_findings('<Statistic label="Win rate">{rate}</Statistic>')) == 2


def test_adr_rendimento_del_periodo_a_panel_with_the_coloured_return_is_not_found() -> None:
    text = '<Statistic label="Rendimento" className={gainTone(statistics.return_percent)}>'

    assert panel_findings(text) == []
