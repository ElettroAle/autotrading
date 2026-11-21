"""ADR-casi-della-descrizione-negli-scenari (Bug 672): the cases a User Story declares in its description, or a Bug of
it corrects, are scenarios of its .feature; every scenario a pipeline run does not prove, inside a rule too, is bound
by a scenario module, so it runs in the suite.
"""

import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from tools.feature_catalog import feature_files, parse_feature

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
SCENARIO_MODULES = ROOT / "tests" / "scenarios"
PIPELINE = "@pipeline"
BINDING = re.compile(r"""scenarios\(\s*["']([^"']+\.feature)["']""")

# Task 673: the cases of the E0 group, each a scenario of the .feature of its User Story.
E0 = "E0-esecuzione-verificata"
CASES_OF_E0 = {
    f"{E0}/F0.1-accesso-alla-piattaforma/R0.1.1-accesso-riservato-al-ruolo-utente.feature": (
        "La documentazione interattiva offre solo l'accesso con codice di autorizzazione e PKCE",
    ),
    f"{E0}/F0.1-accesso-alla-piattaforma/R0.1.2-tenant-utente-al-primo-accesso.feature": (
        "Al primo accesso nasce un tenant vuoto",
    ),
    f"{E0}/F0.2-conti-di-trading/R0.2.2-lettura-dello-stato-del-conto.feature": (
        "La lettura registra l'apertura delle credenziali senza le credenziali",
        "Un'apertura rifiutata delle credenziali è registrata",
    ),
    f"{E0}/F0.4-procedura-di-verifica/R0.4.1-procedura-di-verifica-dell-esecuzione.feature": (
        "Procedura rifiutata su un asset di un flusso in pausa del conto",
        "Gli ordini della procedura non appartengono a nessun flusso",
        "Le aperture delle credenziali della procedura sono registrate",
    ),
    f"{E0}/F0.5-integrazione-e-rilascio/R0.5.1-controlli-di-qualita-sulle-pull-request.feature": (
        "Il commit integrato ha per titolo il titolo della pull request",
        "La revisione valuta le regole che la pull request porta",
    ),
    f"{E0}/F0.5-integrazione-e-rilascio/R0.5.2-pubblicazione-e-rilascio-in-dev.feature": (
        "Senza rilasci precedenti la prossima versione parte da 0.1.0",
    ),
}

FEATURE_WITH_A_RULE = """# language: it
@R0.4.1
Funzionalità: R0.4.1 Procedura

  Regola: una regola

    Scenario: Uno scenario nella regola
      Quando qualcosa accade
      Allora qualcosa si vede
"""
FEATURE_PROVED_BY_THE_PIPELINE = """# language: it
@R0.5.2 @pipeline
Funzionalità: R0.5.2 Rilascio

  Scenario: Uno scenario della pipeline
    Quando qualcosa accade
    Allora qualcosa si vede
"""


def _is_proved_by_the_pipeline(node: Mapping[str, Any]) -> bool:
    return any(tag["name"] == PIPELINE for tag in node["tags"])


def _scenarios_in(children: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for child in children:
        if "scenario" in child:
            yield child["scenario"]
        if "rule" in child:
            yield from _scenarios_in(child["rule"]["children"])


def scenario_names(feature: Mapping[str, Any]) -> list[str]:
    return [scenario["name"] for scenario in _scenarios_in(feature["children"])]


def runs_in_the_suite(feature: Mapping[str, Any]) -> bool:
    """A feature has a scenario the suite runs when one, inside a rule too, is not proved by a pipeline run."""
    if _is_proved_by_the_pipeline(feature):
        return False
    return any(not _is_proved_by_the_pipeline(scenario) for scenario in _scenarios_in(feature["children"]))


def _parsed(text: str, tmp_path: Path) -> dict[str, Any]:
    path = tmp_path / "R0.0.0-example.feature"
    path.write_text(text, encoding="utf-8")
    return parse_feature(path)


def bound_features() -> set[str]:
    return {
        binding
        for module in SCENARIO_MODULES.rglob("test_*.py")
        for binding in BINDING.findall(module.read_text(encoding="utf-8"))
    }


def test_adr_casi_della_descrizione_negli_scenari_a_scenario_inside_a_rule_runs_in_the_suite(tmp_path: Path) -> None:
    assert runs_in_the_suite(_parsed(FEATURE_WITH_A_RULE, tmp_path))
    assert scenario_names(_parsed(FEATURE_WITH_A_RULE, tmp_path)) == ["Uno scenario nella regola"]


def test_adr_casi_della_descrizione_negli_scenari_a_feature_proved_by_the_pipeline_needs_no_module(
    tmp_path: Path,
) -> None:
    assert not runs_in_the_suite(_parsed(FEATURE_PROVED_BY_THE_PIPELINE, tmp_path))


def test_adr_casi_della_descrizione_negli_scenari_every_feature_of_e0_run_by_the_suite_is_bound() -> None:
    # The features of the dashboard are bound by its Playwright scenarios (ADR 0116), not by a module of pytest-bdd.
    unbound = [
        path.relative_to(SPECS).as_posix()
        for path in feature_files(SPECS / E0)
        if runs_in_the_suite(parse_feature(path)) and path.relative_to(SPECS).as_posix() not in bound_features()
    ]
    assert unbound == [], "a .feature with scenarios the suite runs needs a scenario module that binds it"


def test_adr_casi_della_descrizione_negli_scenari_the_cases_of_e0_are_scenarios() -> None:
    missing = {
        path: sorted(set(cases) - set(scenario_names(parse_feature(SPECS / path))))
        for path, cases in CASES_OF_E0.items()
    }
    assert {path: cases for path, cases in missing.items() if cases} == {}
