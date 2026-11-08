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
  integration/<tecnologia>/test_<adapter>.py      adapter contro la tecnologia vera
  scenarios/<E..>/<F..>/test_<Rx_y_z>.py          scenari di specs/ con pytest-bdd
  fakes/<nome_porta>.py                           Fake*/InMemory*Adapter, uno per porta
```

## Regole

- **Unit test per ogni tipo di produzione** che nasce o cambia, sui comportamenti e sui casi limite.
  Uno scenario che attraversa un tipo non lo copre.
- **Scenari**: un modulo per file `.feature`, che lo lega con `scenarios(...)`; `bdd_features_base_dir`
  punta a `specs/`. Eseguiti sui casi d'uso costruiti con gli adapter finti. Ogni `Allora` e ogni `E`
  ha una propria asserzione.
- **Integrazione**: marker `integration`. PostgreSQL e OpenBao in container. Hyperliquid solo con il
  marker `testnet`, fuori dalla suite di default.
- **Test architetturale**: fa parte della suite di default; un contratto rotto è un test rosso.
- **Adapter finti**: implementano la porta per intero, sono deterministici e vivono solo in
  `tests/fakes/`. Mai mock generici al posto di un finto quando la porta è del progetto.
- **Rosso prima del verde**: ogni prova si osserva fallire per il motivo giusto prima di passare.
- Nomi dei test: il comportamento atteso in inglese, es. `test_rejects_leverage_above_exchange_maximum`.
- Configurazione pytest: layout `src`, `--import-mode=importlib`, `--strict-markers`.
- I principi di codice di `CLAUDE.md` valgono anche nei test.
