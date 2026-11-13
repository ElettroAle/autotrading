---
paths:
  - "forecaster/**"
  - "src/autotrading/adapters/outbound/forecaster/**"
  - "tests/unit/forecaster/**"
  - "tests/unit/adapters/forecaster/**"
  - "tests/integration/forecaster/**"
---

# Forecaster: servizio Prophet e adapter in uscita

- **Servizio** (`forecaster/`, docs/architecture.md §10, ADR 0107): container proprio sulla rete interna del compose,
  nessuna porta pubblicata, nessun segreto. Fuori dall'esagono come `tools/`: non importa `autotrading` né i test, e
  `autotrading` non lo importa (lo raggiunge solo via HTTP). Immagine dallo stadio `forecaster` del `Dockerfile`, con
  le sole dipendenze del gruppo `forecaster` di `pyproject.toml`: Prophet, cmdstan, pandas e numpy non entrano
  nell'immagine di `api` e `worker`.
- **Prophet solo in `forecaster/prophet_model.py`**: è l'unico modulo che importa `prophet`, `pandas`, `numpy`,
  `cmdstanpy` (verificato da `tests/architecture/test_forecaster_service.py`).
- **API interna**: `POST /forecast {asset, history_days, points, horizons_minutes}` risponde per ogni orizzonte prezzo
  previsto e intervallo; `GET /health`. Lo storico lo manda il worker, letto dall'exchange: il servizio non parla con
  Hyperliquid.
- **Modelli in cache** per asset e profondità, serializzati in JSON (mai pickle), condivisi tra i flussi; riaddestrati
  solo quando più vecchi di `FORECASTER_RETRAIN_MINUTES` (configurazione pubblica del compose), partendo dai parametri
  del modello precedente.
- Filesystem in sola lettura con `/tmp` in tmpfs: cmdstan e matplotlib scrivono solo file temporanei. Limite di
  memoria nel compose.
- **Adapter** (`adapters/outbound/forecaster/`): un sistema integrato = l'API interna del forecaster, raggiunta con
  `httpx`. Realizza la porta della previsione del contesto `sources`; ogni errore di rete, stato o forma inattesa
  diventa `SourceUnavailableError("forecast")` e la fonte risulta mancante per quel ciclo.
- Test: unit test del servizio con Prophet vero su serie piccole; test di integrazione contro il container costruito
  dalla pipeline (`TEST_FORECASTER_URL`).
