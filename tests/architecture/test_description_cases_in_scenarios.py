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

# Task 676: the cases of E2.
E2 = "E2-dashboard-e-confronto"
CASES_OF_E2 = {
    f"{E2}/F2.1-accesso-e-infrastruttura/R2.1.1-accesso-alla-dashboard.feature": ("Primo accesso con un tenant nuovo",),
    f"{E2}/F2.2-monitoraggio/R2.2.2-stato-e-riepilogo-dei-flussi.feature": (
        "Conto, modello ed esito dell'ultima esecuzione",
        "Rendimento in pareggio in grigio",
    ),
    f"{E2}/F2.2-monitoraggio/R2.2.4-posizioni-aperte.feature": ("PnL corrente anche in percentuale del margine",),
    # Task 677: the statistics and the duplication also from the programmatic interface.
    f"{E2}/F2.2-monitoraggio/R2.2.6-statistiche-del-flusso.feature": ("Statistiche dall'interfaccia programmatica",),
    f"{E2}/F2.2-monitoraggio/R2.2.5-posizioni-chiuse.feature": (
        "Direzione, istanti, commissioni e motivo della chiusura",
        "Importi senza valuta se la valuta del conto non è disponibile",
    ),
    # Task 677: Bug 616, the compact list of the accounts and the page of an account in tabs.
    f"{E2}/F2.3-configurazione-e-comandi/R2.3.1-conti-dalla-dashboard.feature": (
        "Elenco compatto dei conti",
        "Pagina del conto a schede",
    ),
    f"{E2}/F2.3-configurazione-e-comandi/R2.3.4-comandi-dei-flussi-dalla-dashboard.feature": (
        "Archiviazione con conferma",
    ),
    f"{E2}/F2.3-configurazione-e-comandi/R2.3.5-versioni-della-configurazione.feature": (
        "Confronto del system prompt cambiato",
        "La riga del system prompt c'è anche quando non cambia",
    ),
    f"{E2}/F2.3-configurazione-e-comandi/R2.3.10-avviso-della-rete-di-test.feature": (
        "L'avviso della rete di test è giallo",
        "L'avviso della rete reale è rosso",
    ),
    f"{E2}/F2.4-confronto-tra-flussi/R2.4.1-duplicazione-di-un-flusso.feature": (
        "L'avvio di una bozza verifica anche conto e capitale",
        "Duplicazione dall'interfaccia programmatica",
    ),
    f"{E2}/F2.4-confronto-tra-flussi/R2.4.2-classifica-dei-flussi.feature": (
        "PnL, commissioni, win rate, operazioni e costo del modello nella classifica",
        "Bozze e flussi archiviati fuori dalla classifica",
    ),
    f"{E2}/F2.5-storico-ed-esportazione/R2.5.1-storico-interrogabile.feature": (
        "Scelte in rapida successione si sommano",
    ),
}
# Task 677: the cases of E3.
E3 = "E3-rischio-capitale-e-qualita"
CASES_OF_E3 = {
    f"{E3}/F3.1-piano-di-uscita-e-protezione/R3.1.2-stop-loss-e-take-profit-sull-exchange.feature": (
        "La modifica dei predefiniti vale per le aperture successive",
        "I flussi già esistenti ricevono lo stop loss predefinito",
    ),
    f"{E3}/F3.1-piano-di-uscita-e-protezione/R3.1.3-aggiornamento-di-stop-e-obiettivo.feature": (
        "Nuova condizione di invalidazione",
        "Un aggiornamento senza stop non toglie lo stop",
        "Il piano aggiornato è quello che la dashboard mostra",
    ),
    f"{E3}/F3.1-piano-di-uscita-e-protezione/R3.1.4-confidenza-e-soglia-minima.feature": (
        "Confidenza della risposta fuori dall'intervallo",
        "L'aggiornamento del piano non dipende dalla confidenza",
        "La modifica della confidenza minima crea una versione",
    ),
    f"{E3}/F3.2-limiti-di-rischio/R3.2.1-esposizione-complessiva-massima.feature": (
        "Residuo sotto l'importo minimo dell'exchange",
        "Il limite complessivo si applica dopo quello per operazione",
        "Limite complessivo sul valore fuori dall'intervallo",
        "La modifica dei limiti complessivi crea una versione",
    ),
    f"{E3}/F3.2-limiti-di-rischio/R3.2.2-perdita-massima-del-flusso.feature": (
        "Un aumento del capitale non è un guadagno",
        "Aggiornamento del piano deciso durante la sospensione",
        "Con ripresa il giorno dopo l'utente conferma prima",
        "La modifica di una soglia crea una versione",
        "La modifica della ripresa crea una versione",
    ),
    f"{E3}/F3.2-limiti-di-rischio/R3.2.3-chiusura-di-emergenza.feature": (
        "Flussi fermi o archiviati non toccati",
        "Il comando si registra con data, ora, ambito ed esito",
    ),
    f"{E3}/F3.3-riconciliazione/R3.3.1-allarme-sul-saldo-non-spiegato.feature": (
        "Aggiornamento del piano deciso durante l'allarme",
        "La conferma si registra con data e ora",
    ),
    f"{E3}/F3.4-capitale/R3.4.2-storico-delle-variazioni-di-capitale.feature": (
        "Storico a pagine dalla variazione più recente",
    ),
    f"{E3}/F3.4-capitale/R3.4.3-rendimento-corretto-dopo-incassi-e-variazioni.feature": (
        "Il riepilogo del flusso usa lo stesso rendimento",
    ),
    f"{E3}/F3.5-notifiche/R3.5.1-eventi-notificabili-completi.feature": (
        "Le notifiche dei nuovi eventi non contengono credenziali",
    ),
    f"{E3}/F3.5-notifiche/R3.5.2-notifiche-via-email.feature": (
        "Un invio fallito si ritenta",
        "Un'email non contiene mai credenziali",
    ),
    f"{E3}/F3.5-notifiche/R3.5.3-scelta-dei-canali-delle-notifiche.feature": (
        "Un canale non collegato non riceve la notifica",
        "Il campanello riceve ogni notifica qualunque sia la scelta",
    ),
    f"{E3}/F3.5-notifiche/R3.5.4-notifiche-leggibili-con-icone-e-stato-del-flusso.feature": (
        "Allarme del conto senza stato del flusso",
    ),
    f"{E3}/F3.5-notifiche/R3.5.5-server-di-posta-dell-utente.feature": (
        "Senza mittente l'email parte a nome dell'utente",
        "Le notifiche email partono dal server del tenant della notifica",
        "La pagina Notifiche si apre su Canali senza canali collegati",
        "La pagina Notifiche si apre su Preferenze con un canale collegato",
    ),
    f"{E3}/F3.6-qualita-delle-previsioni/R3.6.1-errore-medio-della-previsione.feature": (
        "Prezzo effettivo letto dall'exchange da cui viene la previsione",
    ),
}
# Task 678: the cases of E4, E5 and E6.
E4 = "E4-replay-e-analisi"
CASES_OF_E4 = {
    f"{E4}/F4.1-fonti-ad-adapter-configurabili/R4.1.1-fonti-con-adapter-dichiarati.feature": (
        "Il modulo di un adapter nasce dalla sua dichiarazione",
    ),
    f"{E4}/F4.1-fonti-ad-adapter-configurabili/R4.1.2-credenziali-degli-adapter-delle-fonti.feature": (
        "Un solo avviso per la credenziale rifiutata",
    ),
}
E5 = "E5-evoluzioni"
CASES_OF_E5 = {
    f"{E5}/F5.1-nuove-fonti/R5.1.2-volumi-e-order-book.feature": ("Più exchange con l'aggregato pesato sui volumi",),
    f"{E5}/F5.1-nuove-fonti/R5.1.5-forecast-su-orizzonti-lunghi.feature": (
        "Previsione a 1 settimana",
        "Storico giornaliero più corto della profondità richiesta",
        "Previsione lunga nella valutazione del forecast",
    ),
}
E6 = "E6-piattaforma-e-operativita"
CASES_OF_E6 = {
    f"{E6}/F6.2-avvisi-e-scadenze/R6.2.1-campanello-delle-notifiche.feature": (
        "Notifica con l'invio Telegram fallito",
        "Notifiche conservate 90 giorni",
    ),
    f"{E6}/F6.2-avvisi-e-scadenze/R6.2.2-avviso-di-scadenza-delle-chiavi.feature": ("Una nuova data azzera le soglie",),
    f"{E6}/F6.2-avvisi-e-scadenze/R6.2.3-centro-degli-avvisi.feature": (
        "Avviso della posizione estranea risolto quando la posizione non c'è più",
        "Avviso del flusso risolto quando il flusso finisce",
        "Avviso della chiave risolto quando la chiave è rimossa",
        "Filtri per gravità e tipo di risorsa",
        "Filtro per periodo",
        "Avvisi risolti conservati 90 giorni",
        "Movimenti non spiegati nel riquadro del conto",
    ),
    f"{E6}/F6.3-strumenti-di-prova/R6.3.1-prova-delle-fonti.feature": (
        "Prova di un adapter con le credenziali del tenant",
        "Prova fallita per un errore permanente",
    ),
    f"{E6}/F6.4-dashboard-su-mobile/R6.4.1-dashboard-leggibile-su-mobile.feature": (
        "Avviso della rete senza parole ripetute",
        "Elenco dei flussi senza legenda degli esiti",
    ),
    f"{E6}/F6.4-dashboard-su-mobile/R6.4.3-pagina-del-flusso-a-schede-con-periodo-comune.feature": (
        "Tornare indietro conserva periodo, intervallo e scheda",
        "Cicli conclusi senza segni sull'equity curve",
        "Barra delle schede intera e visibile su schermo stretto",
    ),
    f"{E6}/F6.4-dashboard-su-mobile/R6.4.4-tabelle-leggibili-e-filtrabili.feature": (
        "Tabella con la prima colonna fissa su schermo largo",
        "Righe come schede su schermo stretto",
    ),
    f"{E6}/F6.4-dashboard-su-mobile/R6.4.5-schede-riconoscibili.feature": ("Schede selezionabili da tastiera",),
    f"{E6}/F6.4-dashboard-su-mobile/R6.4.7-periodo-di-6-ore-e-dall-inizio.feature": (
        "Un indirizzo salvato con il periodo dall'inizio continua ad aprirsi",
    ),
    f"{E6}/F6.4-dashboard-su-mobile/R6.4.8-prossima-esecuzione-nella-panoramica.feature": ("Flusso fermo",),
    f"{E6}/F6.5-usabilita-della-dashboard/R6.5.4-ultima-decisione-nella-panoramica.feature": (
        "Ultima decisione a prescindere dal periodo",
        "Ultima decisione dall'interfaccia programmatica",
    ),
    f"{E6}/F6.5-usabilita-della-dashboard/R6.5.5-storico-delle-decisioni.feature": (
        "Filtro per direzione",
        "Storico a pagine",
    ),
    f"{E6}/F6.5-usabilita-della-dashboard/R6.5.6-legenda-dell-equity-curve.feature": (
        "Legenda del confronto delle equity curve",
    ),
}
CASES = {
    **CASES_OF_E0,
    **CASES_OF_E1,
    **CASES_OF_E2,
    **CASES_OF_E3,
    **CASES_OF_E4,
    **CASES_OF_E5,
    **CASES_OF_E6,
}
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
