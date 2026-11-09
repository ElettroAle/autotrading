# AutoTrading: architettura tecnica

**Stato:** bozza 0.1
**Data:** 8 novembre 2026
**Riferimenti:** requisiti in [`requirements.md`](requirements.md) (v0.3), spunti dalle fonti in [`tech-notes.md`](tech-notes.md), valutazione framework in [`research/frameworks-evaluation.md`](research/frameworks-evaluation.md).

Questo documento traduce i requisiti funzionali in scelte tecniche. Le decisioni prese con il proprietario sono in sezione 1; il resto è proposta motivata, aperta a revisione. I dettagli verificati sulla documentazione delle librerie (Context7, 8 novembre 2026) sono segnalati con **[doc]**.

---

## 1. Decisioni di base (intervista dell'8 novembre 2026)

| Tema | Decisione | Motivo |
|------|-----------|--------|
| Linguaggio backend | **Python 3.15** | SDK ufficiale Hyperliquid, CCXT, Prophet, LangGraph: tutto l'ecosistema di riferimento è Python. |
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
│   ├── pyproject.toml              # uv/poetry, Python 3.15
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

Decisioni dell'8 novembre 2026; gli scenari di riferimento sono in `specs/E0-esecuzione-verificata`.

### 8.1 Accesso degli utenti

- **Solo Entra ID.** Gli utenti si creano esclusivamente in Entra; la piattaforma non registra né invita nessuno. Accede solo chi ha il ruolo applicativo **Utente** nel token (R0.1.1). Il **tenant** nasce al primo accesso di chi ha il ruolo, legato all'identificativo stabile della directory (`oid`), non al nome (R0.1.2). Tenant e utente sono distinti: il tenant ha un identificativo proprio, l'utente (`oid`) ne è membro; in E0 il database impone un tenant per utente.
- **Ruolo applicativo** sull'app registration: `Utente` (accesso alla piattaforma). Nessun ruolo di amministrazione delle credenziali (ADR 0007).
- **Superficie in E0-E1**: sola API REST con pagina OpenAPI interattiva e login Entra (Authorization Code + PKCE). Nessuna CLI. Validazione del token con le chiavi pubblicate dall'issuer (JWKS), controllo di audience, tenant e ruolo.
- **Isolamento** (R0.1.3): le porte che il caso d'uso riceve sono già legate al tenant della richiesta; le entità possedute da un tenant estendono `TenantOwned`. Come seconda barriera PostgreSQL applica row level security, configurata e attivata solo dall'adapter SQLAlchemy. Un elemento di un altro tenant risponde "non trovato". Regole in `.claude/rules/context-tenancy.md`.
- **Entra ID, limite da conoscere**: per utenti esterni self-service servirebbe Entra External ID o un altro IdP OIDC; l'app non cambia.

### 8.2 Segreti

**Modello di minaccia.** La gestione dei segreti protegge da: bug nell'API esposta, accesso alla macchina senza privilegi di root, copie di disco, snapshot e backup. Contro un attaccante root sulla macchina in esecuzione nessuno schema su nodo singolo protegge ciò che è in uso; lì contano il valore basso delle chiavi, la rilevazione e la revoca rapida (sotto).

- **Credenziali dei conti cifrate nel database** (ADR 0007): cifratura asimmetrica libsodium (`SealedBox`), una coppia di chiavi per installazione. Accanto al conto si salvano la versione della chiave e il testo cifrato, che contiene anche tenant e conto e viene rifiutato se non coincide con il conto richiesto (R0.2.3).

  | Identità | Chiave | Permessi sulle credenziali dei conti |
  |----------|--------|--------------------------------------|
  | `worker` | privata | lettura (decifratura) |
  | `api` | pubblica | creazione, sostituzione, eliminazione; **mai lettura** |
  | persone | nessuna | **mai lettura** |

  La verifica delle credenziali alla registrazione e alla sostituzione (R0.2.1, R0.2.4) usa le credenziali presenti nella richiesta prima di cifrarle, quindi l'API non ha bisogno di decifrarle. Le funzioni che usano credenziali salvate (stato del conto R0.2.2, ordini R0.3) arrivano con il `worker`.
- **Chiavi**: generate dalla pipeline direttamente sul server al primo deploy, se assenti; la privata è un file leggibile solo da root, montato in sola lettura nel solo container `worker`. Non passano mai da GitHub né da una persona. Rotazione periodica e su richiesta dalla pipeline: requisito futuro R0.2.6; la versione della chiave nel formato salvato la rende possibile senza migrazioni.
- **Segreti dei servizi** (password del database, chiavi dei fornitori dei modelli): segreti degli environment GitHub, consegnati dalla pipeline come file montati in sola lettura, leggibili solo dall'utente del container.
- **Mai variabili d'ambiente per i segreti** (visibili con `docker inspect` e da `/proc`): solo file montati.
- **Registro delle decifrature**: ogni decifratura registra conto e momento, mai il contenuto.
- **LiteLLM**: chiavi dei fornitori come file montati; una chiave virtuale per tenant con budget mensile.

**Limitare il danno se la macchina è compromessa.**

- Credenziali di sola operatività: su Hyperliquid l'API wallet non può prelevare; il wallet principale con i fondi non tocca mai la piattaforma.
- Rilevazione: registro delle decifrature, riconciliazione con allarme, notifica di ogni apertura.
- Revoca: playbook scritto per revocare l'API wallet dal wallet principale e ruotare le chiavi dei servizi.
- Esposizione: solo Caddy (443) e SSH con chiave; `postgres`, `litellm`, `forecaster` su rete interna. Container non root, filesystem in sola lettura dove possibile, nessun accesso al socket Docker.

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

### 12.1 Decisione per F0-F1 (8 novembre 2026)

**Hosting: OVH Public Cloud** (decisione del 9 novembre 2026, ADR 0008; sostituisce la VPS Hetzner, i cui piani condivisi non sono più disponibili). Per ora solo l'installazione `dev`, istanza `d2-2` (1 vCPU, 2 GB, circa €5,71/mese, prezzi di novembre 2026 da verificare all'ordine) in regione `GRA11`, Ubuntu 24.04, Docker Engine, `docker compose`, PostgreSQL in container. Si passa a `d2-4` (2 vCPU, 4 GB, circa €11,44/mese) cambiando una variabile quando arrivano worker e forecaster. Creazione della macchina dalla pipeline con la CLI OpenStack e un service account IAM.

Motivi: canone fisso minimo, sempre acceso, nessun compromesso sull'architettura (cinque container sempre attivi), nessun prerequisito sulla macchina del proprietario.

Alternative scartate e perché:

- **Macchina del proprietario** (VM Windows 11 su Hyper-V): Docker e WSL2 assenti, servirebbe virtualizzazione annidata dall'host, 27 GB liberi, uptime legato alla VM.
- **GitHub Actions come runtime**: il cron non è puntuale (ritardi di decine di minuti, job saltati), nessuno stato, minuti a pagamento oltre 2.000/mese su repo privato, nessun processo sempre attivo per API e LiteLLM. Adatto solo allo "script unico" dei video, non a questa architettura.
- **Oracle Cloud Free Tier** (ARM 4 OCPU / 24 GB gratis): capacità spesso non disponibile, sospensioni di account segnalate, immagini ARM da costruire. Tentabile come esperimento, non come base.
- **Fly.io, Render, Koyeb, Railway**: 8-35 €/mese, ogni servizio fattura a parte.
- **Azure Container Apps**: 30-45 €/mese con PostgreSQL gestito; scala a zero inutile con worker e gateway sempre attivi.

Configurazione del nodo (F0):

1. Ubuntu LTS, utente non root, accesso solo con chiave SSH, firewall `ufw` con sole porte 22 e 443; aggiornamenti automatici di sicurezza.
2. Docker Engine + plugin compose; immagini da GHCR.
3. Reverse proxy (Caddy) davanti ad `api`, con TLS automatico su un nome DNS; `postgres`, `litellm`, `forecaster` su rete interna del compose, mai esposti.
4. Segreti secondo la sezione 8.2: segreti dei servizi come file montati dalla pipeline; coppia di chiavi delle credenziali generata sul server, privata leggibile solo da root.
5. Entra ID: redirect URI sul nome DNS pubblico (e `http://localhost` per lo sviluppo).

**Ambienti e deploy.** Due installazioni identiche, `dev` (reti di test degli exchange) e `prod`, ciascuna sulla propria VPS con la propria coppia di chiavi delle credenziali. Il deploy passa **sempre** dalla pipeline GitHub Actions, con runner ospitati da GitHub: build e pubblicazione delle immagini su GHCR, poi aggiornamento via SSH (chiave privata nei segreti dell'environment GitHub, sulla VPS solo la chiave pubblica). Environment GitHub `dev` e `prod` con segreti separati; `prod` richiede approvazione. Action di terzi fissate per hash di commit; ramo `main` protetto.

**Backup**: in F0 non serve. Da F1, quando i flussi accumulano giorni di cicli (CA-02 richiede 7 giorni), un `pg_dump` notturno in un volume locale più copia su OVH Object Storage o altro storage S3-compatible (pochi centesimi al mese), oppure snapshot dell'istanza. Cosa si perderebbe senza: storico dei cicli, configurazioni versionate, contabilità virtuale, dati per il replay. Nessun denaro, perché il saldo vero sta sull'exchange.

### 12.2 Dopo F1

- Lo stesso `compose.yaml` gira su una VM Azure nel tenant del proprietario (10-20 €) o, con le stesse immagini, su Azure Container Apps con PostgreSQL gestito (30-45 €). Nessun cambio di codice.
- Immagini pubblicate su GHCR dalla CI.
- LLM: 96 cicli/giorno × asset × costo per chiamata, misurato in F1 prima di scegliere il modello di lungo periodo.
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
| T9 | Nodo singolo OVH: nessuna ridondanza, disco locale. | Accettato in testnet; `pg_dump` notturno su storage esterno da F1; lo stesso compose gira altrove in caso di guasto. |
| T10 | Sviluppo locale sulla VM del proprietario senza Docker. | Sviluppare con Python locale contro PostgreSQL e LiteLLM sul nodo OVH (porte via tunnel SSH), oppure installare WSL2/Docker se la virtualizzazione annidata è disponibile. |

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
