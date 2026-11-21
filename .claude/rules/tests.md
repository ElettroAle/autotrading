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
  scenarios/<E..>/<F..>/test_<Rx_y_z>.py          scenari di specs/ con pytest-bdd
  fakes/<nome_porta>.py                           Fake*/InMemory*Adapter, uno per porta
  support/<modulo>.py                             aiuti condivisi dai test che non sono finti di porte
```

## Regole

- **Unit test per ogni tipo di produzione** che nasce o cambia, sui comportamenti e sui casi limite.
  Uno scenario che attraversa un tipo non lo copre.
- **Scenari**: un modulo per file `.feature`, che lo lega con `scenarios(...)`; `bdd_features_base_dir`
  punta a `specs/`. Eseguiti sui casi d'uso costruiti con gli adapter finti. Ogni `Allora` e ogni `E`
  ha una propria asserzione.
- **Tag degli scenari**: solo `@pipeline` (provato da una run reale della pipeline) diventa marker
  pytest ed è escluso dalla suite e dalla copertura degli scenari; gli altri tag (`@R0.5.1`) sono
  tracciabilità e non diventano marker (`tests/scenarios/conftest.py`). `@wip` non esiste: un requisito
  non pianificato non ha il `.feature` in `specs/`, i suoi criteri stanno sulla board.
- **Integrazione**: marker `integration`, per ogni adapter contro la tecnologia vera: PostgreSQL in
  container, testnet Hyperliquid, fornitori IA con una chiave inventata, fonti contro i servizi veri.
  Girano solo nella pipeline, a ogni PR; in locale `addopts` esclude `pipeline` e `integration` e si
  eseguono i test mirati.
- **Nessun test escluso o saltato** (ADR nessun-test-escluso-o-saltato): nessun `pytest.skip`,
  `skipif`, `xfail`, `importorskip` né `mark.skip`; nei test della dashboard nessun `.skip`, `.todo`,
  `.fixme` né `.only`. La pipeline (`.github/actions/pytest-run/action.yml`) esclude solo il marker
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
