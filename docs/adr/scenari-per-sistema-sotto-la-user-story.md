# ADR scenari-per-sistema-sotto-la-user-story — Gli scenari di una User Story stanno in una cartella per sistema

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 683 (Task 691, 692)
- Collegate: ADR 0116 (dashboard e scenari Playwright sui `.feature` di `specs/`), ADR nessun-test-escluso-o-saltato,
  ADR casi-della-descrizione-negli-scenari; `.claude/rules/specs.md`, `.claude/rules/tests.md`,
  `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

Playwright legge cartelle intere di `specs/` (tutto E2 ed E3, F4.1, F6.2-F6.5) e con `missingSteps: 'skip-scenario'`
segna come saltato ogni scenario senza passi TypeScript: gli scenari di logica che pytest-bdd esegue sui casi d'uso
risultano «skipped» nel report di Playwright (277 sul ramo del Bug 672). La regola «nessun test escluso o saltato» lo
vieta, e un report con salti non distingue uno scenario coperto altrove da uno abbandonato.

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): scenari organizzati in cartelle sotto la cartella della User
  Story, una cartella per sistema; i sistemi sono i container dell'architettura (`api`, `worker`, `dashboard`,
  `forecaster`); controllo di copertura al 100% degli scenari di ogni sistema; PR a sé.
- Decisione del proprietario: sulla board gli AC della User Story restano uno solo, con gli scenari di tutti i sistemi,
  ciascun gruppo preceduto dal nome del sistema.
- ADR nessun-test-escluso-o-saltato: nessuno scenario saltato in nessun runner.

## Decisione

- **Percorso**: `specs/E<n>-<slug>/F<n>.<m>-<slug>/R<n>.<m>.<k>-<slug>/<sistema>/R<n>.<m>.<k>-<slug>.feature`, con
  `<sistema>` in `api`, `worker`, `dashboard`, `forecaster`. Una User Story ha almeno un file; nessun `.feature` fuori
  da una cartella di sistema.
- **Contenuto di ogni file**: `# language: it`, tag `@R<n>.<m>.<k>`, `Funzionalità: R<n>.<m>.<k> <titolo>` uguale per
  tutti i file della User Story, la narrativa `Come` / `Voglio` / `Perché`, poi solo le note e gli scenari del
  comportamento che quel sistema realizza. La descrizione sulla board è la terna una volta sola più le note di ogni
  sistema sotto il suo nome; gli AC sono gli scenari di ogni sistema sotto il suo nome.
- **Sistema di uno scenario**: il container che realizza il comportamento. Uno scenario eseguito sui casi d'uso sta nel
  sistema la cui composition monta quel caso d'uso (`api` o `worker`); uno scenario che si prova sulla pagina sta in
  `dashboard`; uno scenario del servizio di previsione sta in `forecaster`. Uno scenario sta in un solo sistema e lo
  esegue un solo runner.
- **Runner**: Playwright legge solo `specs/**/dashboard/*.feature`, con `missingSteps: 'fail-on-gen'` (uno scenario
  senza passi fa fallire la suite) e senza altro filtro che `not @pipeline`; pytest-bdd lega i file di `api`, `worker`
  e `forecaster`. Moduli di scenario: uno per file, `tests/scenarios/<E>/<F>/test_<R>_<sistema>.py` (punti del
  requisito sostituiti da `_`).
- **Copertura per sistema** (`tools/scenario_coverage.py`, job «copertura degli scenari»): uno scenario si identifica
  con il percorso del file e il nome; ogni scenario dei file `dashboard` deve risultare superato nel report di
  Playwright, ogni scenario degli altri sistemi nel report di pytest-bdd, al 100%; uno scenario superato solo dal
  runner sbagliato non conta. `@pipeline` resta escluso dal conteggio come oggi.
- **Strumenti**: `tools/feature_catalog.py`, `tools/gherkin_check.py` e il test
  `tests/architecture/test_description_cases_in_scenarios.py` leggono la struttura nuova.
- **Architettura** (`tests/architecture/`): la regola «nessun test escluso o saltato» rileva anche le opzioni dei runner
  che saltano scenari (`missingSteps` diverso da `fail-on-gen`, `skip-scenario`, filtri per tag che escludono altro che
  `@pipeline`); una regola nuova verifica il percorso dei `.feature` (cartella della User Story, cartella di sistema
  ammessa, nome del file uguale alla cartella della User Story). Ogni regola con un esempio che la viola e uno conforme.
- `.claude/rules/specs.md` e `.claude/rules/tests.md` descrivono il percorso nuovo e i runner per sistema.

## Alternative scartate

- Tag `@dashboard` sugli scenari della pagina con i file dove sono oggi: scartata dal proprietario.
- Due sole cartelle (`dashboard`, `piattaforma`): scartata dal proprietario a favore dei container.
- Lasciare `skip-scenario` con la copertura che incrocia i due report: il report di Playwright mostra test saltati.

## Conseguenze

- Nessuno scenario risulta saltato: ogni runner raccoglie solo gli scenari del proprio sistema.
- Ogni ramo aperto che tocca `specs/` (Bug 672) si riallinea alla struttura nuova prima della sua PR.
- Gli AC della board si riallineano per tutte le User Story spostate.

## Prove

- Suite Playwright con 0 scenari saltati e suite pytest-bdd verdi sulla struttura nuova.
- `tools/scenario_coverage.py`: unit test con uno scenario `dashboard` superato solo da pytest (non coperto) e uno
  `worker` superato solo da Playwright (non coperto).
- Test di architettura delle due regole, ciascuno visto rosso.
