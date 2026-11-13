# ADR 0107 — Previsione dei prezzi con Prophet nel container `forecaster`

- Stato: accettata (13 novembre 2026) per la parte conforme a `docs/architecture.md`; gli scostamenti elencati
  sotto attendono la conferma del proprietario
- Requisiti: R1.3.5 (RF-08.01-RF-08.04); Bug B1.3.5 (186)
- Supera: ADR 0043 (smorzamento di Holt nel domain)
- Collegate: ADR 0006 (immagini Chainguard), ADR 0015 (segreti come file), ADR 0042 (fonti del ciclo)

## Contesto e problema

`docs/architecture.md` prescrive la fonte `forecast` servita da un container interno `forecaster` con Prophet
(righe 38-39, 54, 166, 239, 289, 312, 334 e §10, righe 252-257): servizio separato per non caricare il worker con
cmdstan, API interna `POST /forecast`, modelli serializzati in JSON e in cache per asset, riaddestrati a intervallo
configurabile, previsioni condivise tra i flussi. L'ADR 0043 aveva invece calcolato nel domain lo smorzamento di Holt,
scartando Prophet per peso e tempo: uno scostamento non autorizzato dall'architettura.

Misure (macchina di sviluppo, Python 3.15, Prophet 1.5.0, 3361 punti a 3 minuti, cioè 7 giorni dall'exchange):
addestramento da zero 5,0 s; addestramento partendo dai parametri del modello precedente 0,7 s; previsione di un
istante 0,03 s. Prophet 1.5.0 pubblica ruote `py3-none-manylinux_2_28` con cmdstan incluso; numpy, pandas e
matplotlib hanno ruote per CPython 3.15: nessun problema di versione di Python.

## Decisione

### Servizio `forecaster/` (fuori dall'esagono)

- Pacchetto Python a livello della radice, come `tools/`: non importa `autotrading` né i test e `autotrading` non lo
  importa; il worker lo raggiunge solo via HTTP. Un esagono dentro un servizio di tre moduli non aggiungerebbe nulla:
  il servizio non ha regole di business, solo un modello statistico dietro un'API.
- Dipendenze nel gruppo `forecaster` di `pyproject.toml` (Prophet, FastAPI, uvicorn), installate solo nell'immagine
  del forecaster e nell'ambiente di sviluppo (`uv sync --all-groups`): Prophet, cmdstan, pandas e numpy non entrano
  nell'immagine di `api`, `worker` e `migrate` (`uv sync --no-dev` non installa altri gruppi).
- `forecaster/prophet_model.py` è l'unico modulo che importa `prophet`, `pandas`, `numpy`, `cmdstanpy`; lo verifica
  `tests/architecture/test_forecaster_service.py`, con esempi che violano e conformi per ogni regola.
- API: `POST /forecast {asset, history_days, points: [{at, price}], horizons_minutes}` risponde per ogni orizzonte
  `predicted_price`, `lower_price`, `upper_price` (l'intervallo di Prophet, con 100 campioni); `GET /health`. Prezzi
  come stringhe decimali. Uno storico con meno di 3 punti è rifiutato (422).
- Cache dei modelli (`forecaster/models.py`) per asset e profondità dello storico, condivisa da tutti i flussi e da
  tutti i tenant (i prezzi dell'exchange sono pubblici): un modello si riaddestra solo quando l'ultimo punto ricevuto
  è più recente del suo di almeno `FORECASTER_RETRAIN_MINUTES` (predefinito 15, configurazione pubblica del compose),
  partendo dai parametri del modello precedente (`warm_start_params`). Modelli serializzati in JSON con
  `model_to_json`, mai pickle.

### Immagine e installazione

- Stadio `forecaster` del `Dockerfile`, sulle stesse immagini Chainguard fissate per digest dell'immagine principale;
  l'ultimo stadio resta il predefinito (api, worker, migrate).
- Pipeline: `artefatto` costruisce, scansiona con Trivy e pubblica anche l'immagine del forecaster, nello stesso
  repository GHCR con il tag `<versione>-forecaster`; il rilascio scrive `FORECASTER_IMAGE` (digest) nel `.env`
  dell'installazione; la promozione aggiunge il tag di rilascio allo stesso digest, senza ricostruire. Il controllo
  `test` costruisce l'immagine e la avvia come nel compose (sola lettura, `/tmp` in tmpfs) per i test di
  integrazione; `vulnerabilità` la scansiona.
- Compose: servizio `forecaster` sulla rete interna, nessuna porta pubblicata, nessun segreto, filesystem in sola
  lettura con `/tmp` in tmpfs, `mem_limit: 768m` perché un addestramento non tolga memoria a PostgreSQL, `api` e
  `worker`.

### Adapter e fonte (seconda PR del Bug)

- `adapters/outbound/forecaster/`: un sistema integrato, l'API interna del forecaster, raggiunta con `httpx`.
  Realizza una porta della previsione del contesto `sources`; ogni errore diventa `SourceUnavailableError("forecast")`
  e la fonte risulta mancante per quel ciclo, che prosegue.
- `ForecastAssetUseCase` legge lo storico dall'exchange (`PriceHistoryPort`, invariata), chiede la previsione al
  forecaster e registra le previsioni come prima; `domain/sources/holt_forecast.py` si elimina.

## Alternative scartate

- **Il forecaster legge lo storico da Hyperliquid** (`{asset, horizon, history_depth}` come in architecture.md:254):
  servirebbe nel servizio un secondo client dell'exchange, con le stesse regole di paginazione e di intervallo delle
  candele già nell'adapter Hyperliquid del worker; il worker ha già lo storico.
- **Un pacchetto con il proprio `pyproject.toml` e il proprio lockfile**: due ambienti e due serie di controlli
  (stile, tipi, copertura, vulnerabilità) da tenere allineati; il gruppo di dipendenze tiene comunque Prophet fuori
  dall'immagine principale.
- **Prophet nell'immagine unica**: 215 MB di dipendenze scientifiche e cmdstan in `api`, `worker` e `migrate`, contro
  l'isolamento chiesto da architecture.md:54.
- **Un repository GHCR separato per il forecaster**: un pacchetto nuovo con permessi propri; un tag con suffisso nello
  stesso repository riusa permessi, token e retention esistenti.

## Confronto con le decisioni scritte

| Fonte | Decisione scritta | Esito |
|-------|-------------------|-------|
| docs/architecture.md:54 | `forecaster` servizio interno per Prophet, isolato perché pesante | conforme |
| docs/architecture.md:239, 289 | `forecaster` solo sulla rete interna, mai esposto | conforme |
| docs/architecture.md:254 | API interna `POST /forecast {asset, horizon, history_depth}` | scostamento 1 |
| docs/architecture.md:255 | modelli in JSON, in cache per asset, riaddestrati a intervallo configurabile | conforme |
| docs/architecture.md:256 | previsioni condivise tra i flussi, registrazione per ciclo | conforme: modelli condivisi, ogni flusso registra la sua previsione |
| docs/architecture.md:273 | passaggio a `d2-4` quando arriva il forecaster | scostamento 2 |
| docs/architecture.md:312 (T3) | servizio separato, cache, riaddestramento a intervalli | conforme |
| CLAUDE.md, Sicurezza | nessun segreto in variabili d'ambiente, deploy solo dalla pipeline | conforme |
| CLAUDE.md, Regola delle dipendenze | librerie tecnologiche solo nella loro cartella | conforme: Prophet solo nel servizio, `httpx` nell'adapter |
| ADR 0043 | Holt nel domain | superata |

## Scostamenti

1. **Lo storico lo manda il worker** invece della sola `history_depth`: il servizio riceve i punti e la profondità
   (`history_days`, usata come chiave della cache). Motivo nelle alternative scartate.
2. **La macchina resta `d2-2`**: il passaggio a `d2-4` è preapprovato, ma la pipeline di provisioning crea la macchina
   da zero (`openstack server create`), con perdita del database di dev. Il limite di memoria del forecaster protegge
   gli altri servizi; se non basta, il passaggio si fa con un provisioning dedicato, deciso dal proprietario.

## Conseguenze

- Un container in più nell'installazione e un'immagine in più per rilascio (stessa versione, digest proprio).
- Il primo ciclo di un asset dopo l'avvio del forecaster paga l'addestramento da zero (circa 5 s sulla macchina di
  sviluppo, di più su una vCPU): entro l'attesa delle fonti del ciclo (fino a 60 s) la fonte arriva, altrimenti
  risulta mancante solo per quel ciclo.
- Un modello diverso (NeuralProphet, RF-08.05) si sostituisce dietro la stessa API, senza toccare worker e domain.
