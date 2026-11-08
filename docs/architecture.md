# AutoTrading: architettura tecnica

**Stato:** bozza 0.1
**Data:** 8 novembre 2026
**Riferimenti:** requisiti in [`requirements.md`](requirements.md) (v0.3), spunti dalle fonti in [`tech-notes.md`](tech-notes.md), valutazione framework in [`research/frameworks-evaluation.md`](research/frameworks-evaluation.md).

Questo documento traduce i requisiti funzionali in scelte tecniche. Le decisioni prese con il proprietario sono in sezione 1; il resto è proposta motivata, aperta a revisione. I dettagli verificati sulla documentazione delle librerie (Context7, 8 novembre 2026) sono segnalati con **[doc]**.

---

## 1. Decisioni di base (intervista dell'8 novembre 2026)

| Tema | Decisione | Motivo |
|------|-----------|--------|
| Linguaggio backend | **Python 3.12** | SDK ufficiale Hyperliquid, CCXT, Prophet, LangGraph: tutto l'ecosistema di riferimento è Python. |
| Esecuzione | **Container**, cloud agnostic | Nessun servizio proprietario di un cloud, a parte i fornitori dei modelli IA. Deve girare uguale su Docker Compose locale, su una VM, su Azure Container Apps o su Railway. Costi minimi. |
| Database | **PostgreSQL 16** (scelta delegata) | Un solo database per tutto: dati di dominio, JSON dei contesti, serie temporali, stato di LangGraph, spesa di LiteLLM. Disponibile ovunque. |
| Orchestrazione dell'agente | **LangGraph** | Grafo tipizzato con fan-out parallelo delle fonti; stessa base per comitato (6.28) e doppio timeframe (6.27). |
| Accesso ai modelli | **LiteLLM proxy** self-hosted | API unica OpenAI-compatible verso oltre 100 fornitori (OpenAI, Anthropic, DeepSeek, Gemini, xAI, Mistral, Kimi, Groq, Azure OpenAI, Bedrock, Vertex, OpenRouter, Ollama) **[doc]**. Chiavi virtuali con budget per tenant e spesa tracciata in PostgreSQL **[doc]**. Cambio modello = configurazione (RF-16). |
| Identità | **OIDC generico**, primo IdP Entra ID | L'applicazione conosce solo issuer, client id e claim; Entra ID è sostituibile con qualunque IdP OIDC. Vedi 7.1 per i limiti con utenti esterni. |
| Dashboard | **React + TypeScript** (fase F2) | Frontend separato che consuma la stessa API programmatica di F1. |
| Budget | Nessun vincolo ora | I costi vengono misurati per flusso (RNF-09) e decisi dopo. |

---

## 2. Vista d'insieme

```
                 ┌────────────────────────────────────────────────────────────┐
                 │                      docker compose / cloud                │
                 │                                                            │
  Utente ──OIDC──┤  ┌──────────┐   ┌───────────┐   ┌──────────┐  ┌────────┐  │
  (browser,      │  │ dashboard│──▶│    api    │──▶│ postgres │◀─│ worker │  │
   CLI, script)  │  │ (F2)     │   │ (FastAPI) │   │          │  │        │  │
                 │  └──────────┘   └───────────┘   └──────────┘  └───┬────┘  │
                 │                                       ▲           │       │
                 │                                       │     ┌─────┴─────┐ │
                 │                                  ┌────┴────┐│ forecaster│ │
                 │                                  │ litellm ││ (Prophet) │ │
                 │                                  └────┬────┘└───────────┘ │
                 └───────────────────────────────────────┼───────────────────┘
                                                         ▼
                    Fornitori IA · Hyperliquid (testnet/mainnet) · fonti esterne · Telegram · SMTP
```

Sei container, tutti sostituibili e tutti senza dipendenze da un cloud specifico:

| Container | Ruolo | Fase |
|-----------|-------|------|
| `postgres` | Unico stato persistente. | F0 |
| `litellm` | Gateway verso i modelli IA; chiavi virtuali per tenant; registro spesa. | F1 |
| `api` | Interfaccia programmatica (RF-21): autenticazione OIDC, tenancy, configurazione versionata, comandi, consultazione. Serve anche la dashboard statica in F2. | F0 |
| `worker` | Pianificatore e ciclo decisionale dei flussi (RF-04), esecuzione ordini, contabilità virtuale, riconciliazione, notifiche. | F1 |
| `forecaster` | Servizio interno per le previsioni Prophet (RF-08), isolato perché pesante (cmdstan) e condivisibile tra flussi. | F1 |
| `dashboard` | Build statica React, servita da `api` o da un server statico. | F2 |

`api` e `worker` sono lo stesso pacchetto Python avviato con comandi diversi: condividono modello di dominio, repository e adapter.

---

## 3. Struttura del repository

```
autotrading/
├── backend/
│   ├── pyproject.toml              # uv/poetry, Python 3.12
│   └── autotrading/
│       ├── api/                    # FastAPI: router per tenant, conti, flussi, cicli, comandi
│       ├── worker/                 # scheduler, esecuzione cicli, riconciliazione, notifiche
│       ├── core/                   # dominio: modelli, contabilità virtuale, rischio, versioning
│       ├── graph/                  # LangGraph: stato del ciclo, nodi, grafi (agente unico, comitato, strategico)
│       ├── sources/                # fonti dati: interfaccia + un modulo per fonte
│       ├── exchanges/              # adapter exchange: interfaccia + hyperliquid + simulato (replay)
│       ├── llm/                    # client verso LiteLLM, schema output, costi
│       ├── notify/                 # telegram, email
│       ├── db/                     # SQLAlchemy 2 + Alembic
│       └── settings.py
├── forecaster/                     # servizio Prophet (FastAPI minimale)
├── dashboard/                      # React + TypeScript (F2)
├── deploy/
│   ├── compose.yaml                # sviluppo e produzione piccola
│   ├── litellm/config.yaml
│   └── env.example
├── docs/
└── .github/workflows/              # lint, test, build immagini su GHCR
```

---

## 4. Modello dei dati

Tutte le tabelle di dominio hanno `tenant_id`; l'API filtra sempre per il tenant dell'utente autenticato (RF-01.02) e PostgreSQL applica in più **row level security** con `SET app.tenant_id` per sessione, come seconda barriera.

| Tabella | Contenuto | Requisiti |
|---------|-----------|-----------|
| `tenants`, `users` | Tenant e utenti (subject OIDC, email, ruolo). | 6.1 |
| `accounts` | Conti di trading: exchange, ambiente, indirizzo principale, credenziali **cifrate**, soglia di riconciliazione. | 6.2 |
| `flows` | Identità e stato del flusso (attivo, pausa, fermo, archiviato), puntatore alla versione di configurazione corrente. | 6.3 |
| `flow_config_versions` | Configurazione completa come JSONB, immutabile, numerata; una riga per modifica. | RF-21.03 |
| `capital_allocations` | Movimenti di capitale allocato per flusso: allocazione, riduzione, incasso, con motivo. | 6.22 |
| `cycles` | Un ciclo: flusso, versione config, istante pianificato ed effettivo, esito, durata, costo. | 6.20 |
| `source_samples` | Dati raccolti: fonte, asset, istante di riferimento, payload JSONB. Condivisibili tra flussi (chiave: fonte, asset, istante, parametri). | RF-05.06 |
| `cycle_contexts` | Contesto inviato all'agente (testo o JSON) e risposta integrale. | RF-20.01 |
| `decisions` | Decisione per asset interpretata: azione, direzione, quota, leva, exit plan, confidenza, ragionamento. | 6.17 |
| `risk_outcomes` | Per ogni decisione: originale, modificata, bloccata, motivo. | RF-18.10 |
| `orders`, `fills` | Ordini inviati (con `cloid`) ed eseguiti letti dall'exchange. | 6.19 |
| `positions` | Posizioni virtuali per flusso, aperte e chiuse, con motivo di chiusura. | 6.13 |
| `ledger_entries` | Scritture della contabilità virtuale (margine, PnL realizzato, commissioni, funding). | 6.13 |
| `equity_snapshots` | Istantanea per flusso a ogni ciclo. | RF-13.05 |
| `forecasts` | Previsioni per asset e orizzonte, con prezzo effettivo a scadenza. | 6.8, RF-26.01 |
| `llm_calls` | Ogni chiamata: modello, token, costo, latenza, ciclo, ruolo (agente, analista, gestore). | RF-16.06 |
| `reconciliations` | Esiti delle riconciliazioni per conto. | RF-13.06 |
| `notifications` | Eventi notificati, canale, esito. | 6.24 |
| `models_catalog` | Fornitori e modelli disponibili, parametri ammessi, data di cutoff. | RF-16.05, RF-28.10 |

Serie temporali (`source_samples`, `equity_snapshots`, `forecasts`) partizionate per mese. TimescaleDB non necessario in F1; opzione futura, resta PostgreSQL.

---

## 5. Il ciclo decisionale come grafo LangGraph

Stato del grafo: un modello Pydantic `CycleState` (flusso, versione config, istante, stato del capitale, campioni per fonte, contesto, decisioni, esiti rischio, esiti esecuzione, errori). LangGraph accetta stati Pydantic e valida l'input del primo nodo **[doc]**.

```
START ─▶ load_state ─▶ ┌ source:indicators ┐
                       │ source:pivots     │  (fan-out parallelo, un nodo per fonte attiva,
                       │ source:forecast   │   reducer operator.add sui campioni) [doc]
                       │ source:sentiment  │
                       └ source:news       ┘
                 ─▶ compose_context ─▶ decide ─▶ risk_filter ─▶ execute ─▶ update_ledger ─▶ persist ─▶ notify ─▶ END
```

- **Fonti attive e pesi** vengono letti dalla configurazione del flusso: il grafo viene costruito a ogni ciclo con i soli nodi delle fonti attive (RF-05.02). Il fallimento di un nodo fonte scrive un errore nello stato e il ciclo prosegue (RF-04.05).
- **decide**: chiamata a LiteLLM con output strutturato (schema Pydantic della decisione per asset); risposta non conforme = ciclo registrato senza ordini (RF-17.10).
- **risk_filter**: codice deterministico, senza LLM (sezione 6.18).
- **execute**: adapter exchange; ogni ordine porta `cloid` = identificativo univoco del ciclo e dell'asset (RF-19.07).
- **Checkpointer** LangGraph su PostgreSQL **[doc]** usato per ripresa e debug; la verità contabile resta nelle tabelle di dominio, scritte da `persist`.
- **Comitato (6.28)**: stesso stato, nodo `decide` sostituito dal sottografo planner → analisti (fan-out) → dibattito → gestore.
- **Strategico (6.27)**: secondo grafo, più corto, pianificato al suo intervallo; scrive la narrativa in tabella; il grafo esecutivo la legge in `compose_context`.

### 5.1 Pianificazione ed esecuzione nel worker

- Un processo `worker` con loop asyncio; per ogni flusso attivo un job con l'intervallo configurato (APScheduler, job store in PostgreSQL).
- **Nessuna sovrapposizione** (RF-04.07): advisory lock PostgreSQL per flusso; se il lock è occupato il ciclo viene saltato e registrato.
- Più repliche del worker sono possibili senza coordinamento aggiuntivo grazie al lock: scalabilità orizzontale gratuita.
- Modifica di configurazione: il job legge la versione corrente all'inizio di ogni ciclo (RF-21.04).

---

## 6. Interfacce delle capacità ortogonali

Tre protocolli Python (`typing.Protocol`) con registro per nome; una nuova implementazione si aggiunge registrandola, senza toccare il ciclo (RNF-11).

### 6.1 Fonte dati

```python
class DataSource(Protocol):
    name: str
    params_schema: type[BaseModel]          # parametri configurabili per flusso (RF-05.04)
    supports_history: bool                  # utilizzabile nel replay (RF-25.02)
    async def fetch(self, assets: list[str], at: datetime, params: BaseModel) -> list[SourceSample]: ...
    def render(self, samples: list[SourceSample], weight: float) -> str   # testo per il contesto
```

Fonti F1: `indicators` (candele dall'exchange, calcolo con pandas-ta), `pivots`, `forecast` (chiama `forecaster`), `sentiment` (CoinMarketCap Fear & Greed), `news` (RSS). F5: `whales`, `volumes`.

### 6.2 Modello IA

Nessun adapter per fornitore: il client parla con LiteLLM via SDK OpenAI (`base_url` del proxy). Il "fornitore" nella configurazione del flusso è il nome modello di LiteLLM (`provider/model`). Per ogni chiamata si passano metadata (tenant, flusso, ciclo, ruolo) usati da LiteLLM per il registro spesa **[doc]**. Parametri per flusso: temperatura, limite token, livello di ragionamento se supportato. Il catalogo (`models_catalog`) è sincronizzato dalla configurazione di LiteLLM.

### 6.3 Exchange

```python
class ExchangeAdapter(Protocol):
    async def account_state(self) -> AccountState            # saldo, margine, posizioni reali
    async def candles(self, asset, interval, start, end) -> list[Candle]
    async def market_meta(self, asset) -> MarketMeta         # tick, lot, leva massima, importo minimo
    async def set_leverage(self, asset, leverage, isolated=True) -> None
    async def open(self, asset, side, size, cloid, slippage) -> OrderResult
    async def close(self, asset, cloid) -> OrderResult
    async def place_protection(self, asset, side, size, stop, take, cloid) -> list[OrderResult]
    async def fills_since(self, since) -> list[Fill]
```

Implementazioni: `hyperliquid` (SDK ufficiale) e `simulated` (replay, RF-25.04). CCXT tenuto come alternativa: supporta Hyperliquid con sandbox, `clientOrderId`, `subAccountAddress`, `setLeverage` **[doc]**, utile se si aggiungono altri exchange.

---

## 7. Dettagli verificati su Hyperliquid [doc]

- **Testnet**: stesso SDK, `base_url=constants.TESTNET_API_URL`; la firma seleziona automaticamente Testnet.
- **API wallet (agent wallet)**: chiave separata approvata dal conto principale con `approveAgent`; **firma soltanto**, non può prelevare. Conferma l'assunzione A3 / RNF-05: le credenziali di trading sono quelle dell'API wallet, mai la chiave del wallet principale. Scadenza impostabile, massimo 180 giorni: serve un promemoria di rinnovo (notifica).
- **Query**: i dati del conto si leggono con l'indirizzo del conto principale, non con quello dell'API wallet (errore comune che restituisce stato vuoto). Nel SDK: `Exchange(wallet_agent, TESTNET_API_URL, account_address=indirizzo_principale)`.
- **Nonce per firmatario**: un API wallet per processo che firma. Con più repliche del worker, un API wallet per replica (massimo 3 con nome per conto, più 2 per sub-account).
- **Sub-account**: disponibili solo dopo 100.000 $ di volume (fino a 10). Non utilizzabili in testnet all'inizio: conferma la scelta funzionale della **contabilità virtuale** come meccanismo primario e dei sub-account come opzione futura.
- **Ordini**: `market_open(name, is_buy, sz, px, slippage, cloid)` piazza un limite IOC con scostamento massimo; `cloid` è un identificativo a 128 bit (UUID del ciclo+asset). Stop loss e take profit come ordini trigger `reduceOnly`.
- **Dati**: `candles_snapshot(coin, "15m"|"1h"|"4h", start, end)`, `user_state(address)` (posizioni, margine, liquidazione, `withdrawable`), `user_fills_by_time`, `user_funding_history` per attribuire funding alla contabilità del flusso.
- **Importo minimo** 10 $ per ordine; arrotondamenti su tick e lot da `meta`.

---

## 8. Sicurezza e multi-tenant

- **Autenticazione**: OIDC Authorization Code + PKCE per la dashboard, bearer JWT per API e script. Validazione firma e claim con JWKS dell'issuer. Mappa `sub` → `users.oidc_subject`; primo accesso crea l'utente solo se abilitato dal proprietario (RF-01.04).
- **Entra ID, limite da conoscere**: un tenant Entra "workforce" ospita bene utenti interni e guest invitati; per utenti esterni self-service serve Entra External ID o un altro IdP. Finché gli utenti sono pochi e invitati, Entra ID basta. L'app non cambia in entrambi i casi.
- **Segreti degli utenti** (chiavi API wallet, API key fonti): cifrati a riposo con AES-GCM, chiave radice in variabile d'ambiente (`SECRETS_KEY`), ruotabile; mai restituiti dall'API, mai nei log, mai nel contesto LLM (RNF-04). Evoluzione: KMS del cloud o Vault, dietro la stessa interfaccia.
- **LiteLLM**: una chiave virtuale per tenant con budget mensile; le API key dei fornitori stanno solo nella configurazione di LiteLLM, non nel database dell'app. Opzione futura: chiavi dei fornitori per tenant ("bring your own key").
- **Rete**: solo `api` (e `dashboard`) esposti; `postgres`, `litellm`, `forecaster` su rete interna del compose.

---

## 9. Contabilità virtuale e riconciliazione

- Ogni fill letto dall'exchange con `cloid` noto viene attribuito al flusso e genera scritture in `ledger_entries` (margine impegnato, PnL realizzato, commissioni). Funding attribuito pro quota alle posizioni aperte del flusso.
- `positions` del flusso = vista sulle scritture; `equity_snapshots` a ogni ciclo.
- **Riconciliazione** (RF-13.06): dopo ogni ciclo e ogni N minuti, `sum(equity flussi) + capitale libero` confrontata con `accountValue` dell'exchange; posizioni reali confrontate con la somma delle posizioni virtuali per asset. Scostamento oltre soglia → allarme, flag `trading_suspended` sul conto (RF-13.07).
- La regola di conflitto (RF-02.05) è un vincolo di validazione della configurazione, più un controllo nel `risk_filter` come difesa in profondità.

---

## 10. Forecaster (Prophet)

- Servizio separato per non caricare il worker con cmdstan; API interna: `POST /forecast {asset, horizon, history_depth}` → previsione con intervallo.
- Prophet accetta dati sub-giornalieri e `make_future_dataframe(freq=...)` a minuti o ore **[doc]**; modelli serializzati in JSON (non pickle) **[doc]** e messi in cache per asset, riaddestrati a intervallo configurabile.
- Le previsioni sono condivise tra flussi dello stesso asset e orizzonte (RF-04.09 anticipato per questa fonte, con registrazione per ciclo).
- Alternativa futura dietro la stessa API: NeuralProphet o modelli di altro tipo (RF-08.05).

---

## 11. Replay storico (F4)

- Stesso grafo, con due sostituzioni per iniezione: `clock` simulato e `ExchangeAdapter = simulated` (commissioni, importo minimo, slippage, trigger su candele storiche, RF-25.04).
- Fonti con `supports_history=True` ricevono `at` simulato; le altre risultano assenti nel contesto (RF-25.02). Garanzia di **nessun dato futuro**: il repository di `source_samples` filtra per `reference_time <= at` (RF-25.03).
- Stima costi prima dell'avvio: numero cicli × numero asset × chiamate per ciclo × costo medio del modello da `llm_calls` (RF-25.05).

---

## 12. Deployment e costi

- **Sviluppo e produzione piccola**: `docker compose up` con i sei servizi; volumi per PostgreSQL. Lo stesso `compose.yaml` gira su una VM qualsiasi.
- **Cloud**: immagini pubblicate su GHCR dalla CI; qualunque servizio container (Azure Container Apps, Railway, Fly, una VM con Docker). Nessun servizio gestito obbligatorio: PostgreSQL può essere gestito (comodo per backup) o in container.
- **Stima minima** (testnet, 1-3 flussi a 15 minuti): una VM da 2 vCPU / 4 GB o equivalente in container app, circa 15-30 € al mese; PostgreSQL gestito piccolo, 10-20 € se non in container; LLM: 96 cicli/giorno × asset × costo per chiamata, misurato in F1 prima di scegliere il modello di lungo periodo.
- **CI**: GitHub Actions: ruff, mypy, pytest (unit sul rischio e sulla contabilità, integrazione con PostgreSQL in servizio), build immagini. Boards su ADO con `AB#id` nei commit.

---

## 13. Rischi tecnici e punti aperti

| # | Punto | Mitigazione / decisione da prendere |
|---|-------|--------------------------------------|
| T1 | Hyperliquid testnet: faucet, disponibilità ordini trigger, liquidità dei mercati. | Verificare in F0 con la procedura RF-19.05. |
| T2 | LangGraph e LangChain evolvono velocemente (versioni major frequenti). | Fissare le versioni; isolare l'uso in `graph/`; il dominio non importa LangChain. |
| T3 | Prophet: immagine pesante (cmdstan), addestramento lento con storici lunghi. | Servizio separato, cache dei modelli, riaddestramento a intervalli, non a ogni ciclo. |
| T4 | Costo LLM con più flussi e comitato. | Budget per tenant in LiteLLM; stima prima del salvataggio della configurazione (RF-28.08). |
| T5 | Entra ID per utenti esterni self-service. | Entra ID workforce con inviti finché bastano; External ID o altro IdP OIDC dopo, senza cambi nell'app. |
| T6 | Scadenza API wallet (180 giorni). | Campo `expires_at` sul conto, notifica 14 giorni prima. |
| T7 | Nonce con più worker. | Un API wallet per replica; in F1 una sola replica. |
| T8 | Fonti esterne instabili (feed RSS, endpoint non ufficiali). | Isolamento per nodo, timeout, campione mancante registrato; chiusura della fonte se non praticabile (principio dei requisiti). |

---

## 14. Piano tecnico delle prime fasi

**F0. Esecuzione verificata**
1. Scheletro repo, `compose.yaml` con `postgres` e `api`, Alembic, modello `tenants/users/accounts`.
2. Adapter `hyperliquid` su testnet: stato conto, candele, leva, apertura e chiusura con `cloid`, ordini trigger.
3. Comando `verify-execution` (RF-19.05) che apre, legge e chiude; registra ordini e fill.
4. Autenticazione OIDC su `api` con un solo utente abilitato.

**F1. Flussi autonomi senza dashboard**
1. Modello dati completo (sezione 4), configurazione versionata, validazioni (RF-21.05), regola di conflitto.
2. `litellm` in compose, catalogo modelli, client con output strutturato.
3. Fonti `indicators`, `pivots`, `sentiment`, `news`; `forecaster` con Prophet.
4. Grafo del ciclo (sezione 5), rischio base, esecuzione, contabilità virtuale, persistenza, riconciliazione base.
5. Worker con APScheduler e advisory lock; comandi avvio/pausa/stop.
6. Notifiche Telegram essenziali.
7. CI, immagini, deploy di prova su una VM o container app.
