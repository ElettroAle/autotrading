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

# Task 674: the cases of E1 from F1.1 to F1.3.
E1 = "E1-flussi-autonomi"
CASES_OF_E1 = {
    f"{E1}/F1.1-flussi-di-trading/R1.1.3-modifica-versionata-della-configurazione.feature": (
        "Confronto del system prompt tra due versioni",
    ),
    f"{E1}/F1.1-flussi-di-trading/R1.1.4-avvio-pausa-e-ripresa.feature": (
        "Avvio rifiutato se il capitale allocato supera il capitale libero letto ora",
    ),
    f"{E1}/F1.1-flussi-di-trading/R1.1.5-stop-di-un-flusso.feature": (
        "Stop rifiutato per un flusso fermo",
        "Stop rifiutato per un flusso archiviato",
    ),
    f"{E1}/F1.1-flussi-di-trading/R1.1.6-archiviazione-di-un-flusso.feature": (
        "Un flusso archiviato non si avvia",
        "Versioni e posizioni chiuse di un flusso archiviato restano consultabili",
    ),
    f"{E1}/F1.1-flussi-di-trading/R1.1.7-capitale-allocato.feature": (
        "La variazione è registrata con data, ora e utente",
        "Variazione rifiutata per un flusso archiviato",
    ),
    f"{E1}/F1.2-ciclo-decisionale/R1.2.1-cicli-pianificati.feature": (
        "Dopo un'assenza del pianificatore si esegue solo l'ultimo ciclo dovuto",
    ),
    f"{E1}/F1.2-ciclo-decisionale/R1.2.4-pausa-per-errori-permanenti.feature": (
        "Un limite di frequenza del fornitore IA non mette in pausa, anche se parla di quota",
    ),
    f"{E1}/F1.2-ciclo-decisionale/R1.2.5-fonte-non-disponibile.feature": (
        "Una fonte risponde con un errore",
        "Le fonti si interrogano in parallelo",
    ),
    f"{E1}/F1.3-fonti-dati/R1.3.1-catalogo-delle-fonti.feature": (
        "Una fonte aggiunta compare nel catalogo ed è selezionabile",
        "Una fonte ritirata scompare dal catalogo",
    ),
    f"{E1}/F1.3-fonti-dati/R1.3.2-selezione-pesi-e-parametri-delle-fonti.feature": (
        "Fonti, pesi e parametri modificati creano una nuova versione",
    ),
    f"{E1}/F1.3-fonti-dati/R1.3.3-indicatori-tecnici.feature": ("Lunghezza della serie fuori dall'intervallo",),
    f"{E1}/F1.3-fonti-dati/R1.3.4-pivot-point.feature": ("Prezzo sotto l'ultimo supporto",),
    f"{E1}/F1.3-fonti-dati/R1.3.5-forecast.feature": ("Profondità dello storico fuori dall'intervallo",),
    f"{E1}/F1.3-fonti-dati/R1.3.7-notizie.feature": ("Numero di notizie ed età massima fuori dall'intervallo",),
    # Task 675: the cases of E1 from F1.4 to F1.8.
    f"{E1}/F1.4-agente-ia/R1.4.1-chiavi-dei-fornitori-ia.feature": (
        "Rimozione di una chiave che nessun flusso attivo o in pausa usa",
    ),
    f"{E1}/F1.4-agente-ia/R1.4.2-catalogo-dei-modelli.feature": (
        "Un modello aggiunto con la sola configurazione è nel catalogo ed è selezionabile",
    ),
    f"{E1}/F1.4-agente-ia/R1.4.3-contesto-dell-agente.feature": ("Dati e pesi delle fonti attive per ogni asset",),
    f"{E1}/F1.4-agente-ia/R1.4.4-decisione-per-asset.feature": (
        "Chiudi con campi operativi",
        "L'apertura della chiave del fornitore IA è registrata senza la chiave",
        "Un'apertura rifiutata della chiave del fornitore IA è registrata",
    ),
    f"{E1}/F1.4-agente-ia/R1.4.8-system-prompt-personalizzabile.feature": (
        "Il flusso segue il predefinito aggiornato dalla piattaforma",
        "La modifica del system prompt è una nuova versione della configurazione",
    ),
    f"{E1}/F1.4-agente-ia/R1.4.10-inversione-in-un-ciclo.feature": (
        "L'apertura dell'inversione riceve stop e obiettivo sull'exchange",
    ),
    f"{E1}/F1.5-rischio-ed-esecuzione/R1.5.2-leva-massima.feature": (
        "La riduzione della leva precede il controllo dell'esposizione",
    ),
    f"{E1}/F1.5-rischio-ed-esecuzione/R1.5.3-decisioni-incoerenti.feature": (
        "Una chiusura non libera liquidità per le aperture dello stesso ciclo",
    ),
    f"{E1}/F1.5-rischio-ed-esecuzione/R1.5.4-importo-minimo-dell-exchange.feature": (
        "Minimo oltre la liquidità del flusso",
    ),
    f"{E1}/F1.6-capitale-dei-flussi/R1.6.1-stato-del-flusso-dall-exchange.feature": (
        "La liquidità del ciclo non scende sotto zero",
        "Un ordine della piattaforma senza flusso è del flusso che ha l'asset",
    ),
    f"{E1}/F1.6-capitale-dei-flussi/R1.6.2-movimenti-non-attribuibili.feature": (
        "Esecuzione senza identificativo della piattaforma",
    ),
    f"{E1}/F1.6-capitale-dei-flussi/R1.6.3-registro-delle-operazioni.feature": ("Colonne del file esportato",),
    f"{E1}/F1.7-registrazione-e-consultazione/R1.7.1-registrazione-del-ciclo.feature": (
        "Fonte assente nel ciclo registrato",
        "Le credenziali del conto non compaiono nella registrazione",
    ),
    f"{E1}/F1.7-registrazione-e-consultazione/R1.7.2-storico-delle-posizioni-chiuse.feature": (
        "Cicli e istanti di apertura e di chiusura",
    ),
    f"{E1}/F1.7-registrazione-e-consultazione/R1.7.3-consultazione-di-flussi-e-cicli.feature": (
        "Elenco dei flussi con conto, ambiente, pausa automatica e modello",
        "Letture dello stesso conto entro 10 secondi",
        "Nuova lettura dopo 10 secondi",
        "Tenant e conti diversi non condividono la lettura",
        "Una lettura fallita non si riusa",
    ),
    f"{E1}/F1.8-notifiche/R1.8.2-notifiche-essenziali.feature": ("Una notifica non contiene mai credenziali",),
}

CASES = {**CASES_OF_E0, **CASES_OF_E1}
# The epics whose features the scenario modules of pytest-bdd bind; those of the dashboard bind its Playwright
# scenarios (ADR 0116).
EPICS_BOUND_BY_PYTEST = (E0, E1)

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


def test_adr_casi_della_descrizione_negli_scenari_every_feature_run_by_the_suite_is_bound() -> None:
    # The features of the dashboard are bound by its Playwright scenarios (ADR 0116), not by a module of pytest-bdd.
    unbound = [
        path.relative_to(SPECS).as_posix()
        for epic in EPICS_BOUND_BY_PYTEST
        for path in feature_files(SPECS / epic)
        if runs_in_the_suite(parse_feature(path)) and path.relative_to(SPECS).as_posix() not in bound_features()
    ]
    assert unbound == [], "a .feature with scenarios the suite runs needs a scenario module that binds it"


def test_adr_casi_della_descrizione_negli_scenari_the_cases_are_scenarios() -> None:
    missing = {
        path: sorted(set(cases) - set(scenario_names(parse_feature(SPECS / path)))) for path, cases in CASES.items()
    }
    assert {path: cases for path, cases in missing.items() if cases} == {}
