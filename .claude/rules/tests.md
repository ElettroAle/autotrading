---
paths:
  - "tests/**"
  - "pyproject.toml"
---

# Organizzazione dei test

```text
tests/
  architecture/test_import_contracts.py           esegue import-linter sui contratti di pyproject.toml
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
- **Tag degli scenari**: `@wip` (User Story non ancora consegnata) e `@pipeline` (provato da una
  run reale della pipeline) diventano marker pytest e sono esclusi dalla suite di default e dalla
  copertura degli scenari; gli altri tag (`@R0.5.1`) sono tracciabilità e non diventano marker
  (`tests/scenarios/conftest.py`). Consegnare una User Story significa togliere `@wip`.
- **Integrazione**: marker `integration`. PostgreSQL e OpenBao in container. Hyperliquid solo con il
  marker `testnet`, fuori dalla suite di default.
- **Test architetturale**: fa parte della suite di default; un contratto rotto è un test rosso.
- **Adapter finti**: implementano la porta per intero, sono deterministici e vivono solo in
  `tests/fakes/`. Mai mock generici al posto di un finto quando la porta è del progetto.
- **Rosso prima del verde**: ogni prova si osserva fallire per il motivo giusto prima di passare.
- Nomi dei test: il comportamento atteso in inglese, es. `test_rejects_leverage_above_exchange_maximum`.
- Configurazione pytest: layout `src`, `--import-mode=importlib`, `--strict-markers`.
- I principi di codice di `CLAUDE.md` valgono anche nei test.
