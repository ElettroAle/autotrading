---
paths:
  - "tests/**"
  - "pyproject.toml"
---

# Organizzazione dei test

```text
tests/
  architecture/test_import_contracts.py           esegue import-linter sui contratti di pyproject.toml
  architecture/test_layer_separation.py           regole statiche sui layer (CLAUDE.md, Test di architettura)
  architecture/test_architecture_rules.py         ogni regola rossa su un esempio che la viola
  architecture/known_violations.py                violazioni note, ciascuna col suo Bug: solo in calo
  unit/
    domain/<contesto>/test_<modulo>.py            domain puro
    application/<contesto>/test_<caso_d_uso>.py   casi d'uso con adapter finti
    adapters/<tecnologia>/test_<modulo>.py        funzioni di traduzione, senza la tecnologia
    bootstrap/test_bootstrap.py                   composition root
    tools/test_<modulo>.py                        script della pipeline
  integration/<tecnologia>/test_<adapter>.py      adapter contro la tecnologia vera
  scenarios/<E..>/<F..>/test_<Rx_y_z>_<sistema>.py  scenari di specs/ di api, worker e forecaster con pytest-bdd
  fakes/<nome_porta>.py                           Fake*/InMemory*Adapter, uno per porta
  support/<modulo>.py                             aiuti condivisi dai test che non sono finti di porte
```

## Regole

- **Unit test per ogni tipo di produzione** che nasce o cambia, sui comportamenti e sui casi limite.
  Uno scenario che attraversa un tipo non lo copre.
- **Scenari**: un modulo per file `.feature` dei sistemi `api`, `worker` e `forecaster`,
  `tests/scenarios/<E>/<F>/test_<R>_<sistema>.py` (punti del requisito sostituiti da `_`), che lo lega con
  `scenarios(...)`; `bdd_features_base_dir` punta a `specs/`. Eseguiti sui casi d'uso costruiti con gli adapter finti.
  I passi che due file della stessa User Story condividono stanno in `tests/support/`. I file `dashboard` li esegue
  Playwright (`.claude/rules/tech-dashboard.md`). Ogni `Allora` e ogni `E` ha una propria asserzione.
- **Copertura degli scenari per sistema** (`tools/scenario_coverage.py`): ogni scenario non `@pipeline` dei file
  `dashboard` superato nel report di Playwright, di ogni altro sistema nel report di pytest-bdd, al 100%; uno scenario
  superato solo dal runner dell'altro sistema non conta (ADR scenari-per-sistema-sotto-la-user-story).
- **Tag degli scenari**: solo `@pipeline` (provato da una run reale della pipeline) diventa marker
  pytest ed è escluso dalla suite e dalla copertura degli scenari; gli altri tag (`@R0.5.1`) sono
  tracciabilità e non diventano marker (`tests/scenarios/conftest.py`). `@wip` non esiste: un requisito
  non pianificato non ha il `.feature` in `specs/`, i suoi criteri stanno sulla board.
- **Integrazione**: marker `integration`, per ogni adapter contro la tecnologia vera: PostgreSQL in
  container, testnet Hyperliquid per `orders` e `accounts`, fornitori IA con una chiave inventata.
  Girano solo nella pipeline, a ogni PR; in locale `addopts` esclude `pipeline` e `integration` e si
  eseguono i test mirati.
- **Fonti su risposte registrate** (ADR fonti-provate-su-risposte-registrate): i test delle fonti,
  `tests/integration/sources/test_<fonte>_recorded.py` (marker `integration`), non chiamano mai i servizi dal vivo.
  Girano su risposte vere catturate una volta dal vivo e salvate come arrivano in
  `tests/integration/sources/recorded/<tecnologia>/`, ciascuna col proprio `<nome>.recording.json` (richiesta, URL,
  stato, data di registrazione); `tests/support/recorded_answers.py` le serve con `httpx.MockTransport` o come
  trasporto della sessione dell'SDK Hyperliquid e fa fallire il test su una richiesta non registrata. Ogni fonte ha
  almeno una risposta di errore (429 o 5xx). I fornitori a chiave seguono ADR
  risposte-http-registrate-per-i-fornitori-a-chiave.
- **Nessun test escluso o saltato** (ADR nessun-test-escluso-o-saltato): nessun `pytest.skip`,
  `skipif`, `xfail`, `importorskip` né `mark.skip`; nei test della dashboard nessun `.skip`, `.todo`,
  `.fixme` né `.only`; Playwright con `missingSteps: 'fail-on-gen'`, `tags: 'not @pipeline'` e nessun `grep`,
  `grepInvert` né `testIgnore`. La pipeline (`.github/actions/pytest-run/action.yml`) esclude solo il marker
  `pipeline`. Un test che vuole un file di credenziali lo legge e fallisce se manca. Unica eccezione
  nota il marker `testnet_credentials` dei test che mandano ordini sulla testnet, voci di
  `known_violations.py` col Bug 643 finché il segreto delle credenziali non esiste.
- **Test architetturale**: fa parte della suite di default; un contratto rotto, una regola dei
  layer violata o un test escluso è un test rosso. Le regole vivono in `tests/support/architecture.py`.
- **Adapter finti**: implementano la porta per intero, sono deterministici e vivono solo in
  `tests/fakes/`. Mai mock generici al posto di un finto quando la porta è del progetto.
- **Rosso prima del verde**: ogni prova si osserva fallire per il motivo giusto prima di passare.
- Nomi dei test: il comportamento atteso in inglese, es. `test_rejects_leverage_above_exchange_maximum`.
- Configurazione pytest: layout `src`, `--import-mode=importlib`, `--strict-markers`.
- I principi di codice di `CLAUDE.md` valgono anche nei test.
