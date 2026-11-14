# AutoTrading

Piattaforma personale di trading automatico multi-tenant. Fonte di verità del COSA: i file
`specs/**/*.feature` e la board Azure DevOps. `docs/requirements.md` è il raw di partenza,
`docs/architecture.md` raccoglie le decisioni tecniche e infrastrutturali.

Questo file è il contratto del repository: architettura del codice, nomenclatura, principi e
organizzazione dei test sono **decisioni del proprietario**. Non si cambiano senza la sua approvazione.
Le regole di dettaglio per percorso sono in `.claude/rules/` (indice in fondo).

## Lingua

- Conversazione, specifiche Gherkin, descrizioni sulla board, documenti: **italiano**.
- Codice, identificatori, messaggi di commit: **inglese**.
- Termini tecnici senza bisogno di traduzione restano in inglese anche nei testi italiani
  (`tenant`, non "spazio").

## Stack

Python 3.15, uv, ruff, mypy (strict), pytest + pytest-bdd, import-linter. FastAPI, SQLAlchemy 2 +
Alembic, PostgreSQL 16, PyNaCl (libsodium), SDK ufficiale Hyperliquid, LangGraph (ciclo decisionale), APScheduler 3
(pianificazione dei cicli), Entra ID.
Dettagli e motivazioni in `docs/architecture.md`.

## Architettura target

### Container (installazioni `dev` e `prod`, OVH Public Cloud, Docker Compose)

```text
Utente (tailnet) ──HTTPS──> Tailscale Serve ──> api (FastAPI) ──┬──> PostgreSQL (credenziali cifrate, chiave pubblica)
                                            ├──> Hyperliquid (internet)
                                            └──> Entra ID (validazione token)
worker (chiave privata) ──> PostgreSQL, Hyperliquid, litellm, forecaster (Prophet)
fasi successive: dashboard
```

### Esagono dentro un servizio

```text
 ADAPTER IN INGRESSO        NUCLEO                              ADAPTER IN USCITA
 FastAPI router ──> UseCase (application) ──> dominio
                         │ dipende solo da porte (*Port)
                         ├── ExchangePort          ◄── HyperliquidExchangeAdapter
                         ├── CredentialSealerPort  ◄── SodiumCredentialSealerAdapter
                         ├── CredentialOpenerPort  ◄── SodiumCredentialOpenerAdapter
                         └── AccountRepositoryPort ◄── SqlAlchemyAccountRepositoryAdapter
 bootstrap.py: unico punto che sceglie quale adapter sta dietro ogni porta
```

### Flusso di una richiesta

```text
Token Entra ──> adapter FastAPI: valida token, estrae oid e ruoli ──[senza ruolo Utente]──> 403
                  │
                  └──> ResolveTenantUseCase(oid) ──[nessun tenant]──> crea Tenant (R0.1.2)
                         │
                         └──> tenant_id ──> bootstrap.for_tenant(tenant_id)
                                              ├── porte legate al tenant
                                              └── sessione DB con il tenant impostato (RLS)
                                                   └──> UseCase.execute(command)
```

## Struttura: prima il livello, poi il contesto

```text
src/autotrading/
  domain/                       livello 1: regole di business, solo libreria standard
    errors.py                   AutotradingError, DomainError
    tenancy/  accounts/  orders/  verification/
    flows/  sources/  agent/  notifications/
  application/                  livello 2: casi d'uso e porte
    errors.py                   ApplicationError
    <contesto>/
      ports.py                  *Port (typing.Protocol)
      errors.py                 errori di application e dei contratti delle porte
      <verbo>_<oggetto>.py      un caso d'uso per modulo
  adapters/                     livello 3: tecnologie, ognuna incapsulata
    inbound/api/                FastAPI
    outbound/<tecnologia>/      un sistema integrato per cartella: hyperliquid/, libsodium/, sqlalchemy/,
                                json/, oidc/, threads/, system_clock/, telegram/, worker/, rss/,
                                alternative_me/, coinmarketcap/, litellm/, openrouter/, forecaster/,
                                apscheduler/
  bootstrap.py                  composition root
tests/                          vedi .claude/rules/tests.md
specs/                          vedi .claude/rules/specs.md
tools/                          script Python della pipeline, fuori dall'esagono (.claude/rules/ci.md)
forecaster/                     servizio Prophet in un container proprio, fuori dall'esagono (tech-forecaster.md)
dashboard/                      dashboard React + TypeScript in un container proprio, fuori dall'esagono (tech-dashboard.md)
deploy/                         cloud-init, compose e policy Tailscale delle installazioni
.github/                        workflow e action della pipeline TrunkFlow
docs/adr/                       decisioni tecniche, una per file
```

**Contesti** = aree di logica di business, non tecnologie. In E0: `tenancy`, `accounts`, `orders`,
`verification`. In E1: `flows` (con il ciclo decisionale, ADR 0094), `sources`, `agent`, `notifications` (ADR 0026). Un contesto nuovo nasce solo con decisione del proprietario e porta con sé la propria
rule `context-<nome>.md`.

**Comunicazione tra contesti**: chiamata in-process attraverso porte o casi d'uso esposti. Eventi solo
se un singolo design li motiva, con decisione del proprietario.

## Regola delle dipendenze

Le dipendenze puntano solo verso il centro: `adapters` ──> `application` ──> `domain`. Mai il contrario.

- `domain` non importa nulla di `application`, `adapters`, `bootstrap`, né librerie esterne.
- `application` importa solo `domain` e la libreria standard.
- **Eccezione architetturale nominale, decisa dal proprietario** (vincolo di campo, ADR 0104): LangGraph
  orchestra il ciclo decisionale come grafo. `langgraph` si importa solo in
  `application/flows/cycle_graph.py` (il grafo: nodi che chiamano le porte dei passi) e in
  `adapters/outbound/sqlalchemy/cycle_checkpoints.py` (il checkpointer su PostgreSQL). Nessun altro modulo, e
  nessun'altra libreria per analogia.
- Le librerie tecnologiche si importano solo nella cartella del loro adapter, `bootstrap.py` compreso.
- **Un adapter = una e una sola tecnologia**: virtualmente una libreria a sé, staccabile. Tecnologia =
  sistema integrato (Hyperliquid, Telegram, l'API interna del worker, un feed RSS, alternative.me,
  CoinMarketCap, PostgreSQL, libsodium), non la libreria che lo raggiunge: una chiamata HTTP verso
  Telegram sta in `telegram/`, mai in una cartella `httpx/`. Ogni cartella `adapters/<verso>/<tecnologia>/`
  dichiara le sue librerie; una libreria specifica di un sistema (SDK Hyperliquid, `sqlalchemy`, `nacl`,
  `jwt`) appartiene a una sola cartella, una libreria di trasporto (`httpx`) può servire più cartelle.
- Le cartelle `adapters/<verso>/<tecnologia>` non si importano a vicenda.
- **Il caso d'uso orchestra gli adapter; un adapter non orchestra.** Un adapter non riceve porte né casi
  d'uso e da `application` importa solo `ports.py` ed `errors.py`. Unica eccezione il decorator: riceve la
  stessa porta che dichiara di realizzare, per aggiungere un comportamento; prima di un decorator con
  effetti si valuta l'outbox.
- **Niente ponti tra contesti.** Il contesto che usa un dato di un altro dichiara le sue porte, con i suoi
  errori, nel proprio `ports.py`; l'adapter della tecnologia che ha il dato le realizza nella sua cartella
  (un adapter può realizzare più porte); la sequenza sta nel caso d'uso.
- `bootstrap.py` istanzia e collega, come un `Program.cs`: nessuna classe, costante, decisione o
  tecnologia.
- **Configurazione per adapter, come `IConfiguration` in .NET.** L'ambiente del processo e i file dei
  segreti si leggono solo in `adapters/configuration/source.py` (`ConfigurationSource`: `value`,
  `optional`, `secret`, `optional_secret`, `environment`); un segreto è sempre il file indicato da
  `<NOME>_FILE`. Ogni cartella adapter ha `configuration.py`, con le sue impostazioni in una dataclass
  frozen privata `_<Tecnologia>Settings` e la funzione privata che le legge e ne valida forma e presenza,
  e `composition.py`, con le funzioni `<tecnologia>_adapters(source, ...)` che leggono le impostazioni e
  restituiscono adapter pronti (l'equivalente dei metodi di estensione `Add<X>(IConfiguration)`). Il
  costruttore di un adapter riceve impostazioni tipizzate o client, mai la `ConfigurationSource`. Le
  regole di business sui valori restano nel domain. `bootstrap.py` crea la `ConfigurationSource` e la passa
  solo alle funzioni `*_adapters`: nessun nome di variabile, nessun default.
- `adapters/configuration` è l'**unica eccezione per nome** alla separazione delle cartelle adapter: la
  importano solo i `configuration.py` e `composition.py` delle cartelle adapter e `bootstrap.py`, e lei
  non importa alcuna cartella di tecnologia.
- `domain/tenancy` è l'unico contesto che tutti gli altri contesti possono importare.

Verificato da import-linter (contratti in `pyproject.toml`), eseguito da `tests/architecture/`.
Un contratto non si allenta e non si aggiunge un `ignore_imports` senza approvazione del proprietario.

## Test di architettura

`tests/architecture/` verifica la separazione dei layer a ogni esecuzione della suite; una regola
violata è un test rosso con file, riga, regola e dove va il codice. I test sono intransigenti: **nessuna
regola ha eccezioni per nome**.

- Import: i contratti di import-linter; ogni cartella di tecnologia e ogni contesto (tenancy esclusa)
  stanno nel proprio contratto di indipendenza.
- Librerie: ogni cartella di tecnologia dichiara le sue librerie esterne e importa solo quelle; una
  libreria appartiene a una sola cartella, salvo le librerie di trasporto (`httpx`); `domain`,
  `application` e `bootstrap.py` non importano librerie esterne. Unica eccezione `langgraph`, solo nei due moduli
  che la regola delle dipendenze nomina.
- Adapter: non riceve porte né casi d'uso nel costruttore (salvo il decorator della stessa porta,
  dichiarata tra le basi) e da `application` importa solo `ports.py` ed `errors.py`.
- Nessun ponte: nessuna classe `*Bridge*` o `<X>From<Y>`.
- Porte: un `Protocol` o un `*Port` si definisce solo in `application/<contesto>/ports.py`; un
  `Protocol` si chiama `*Port` e un `*Port` è un `Protocol`.
- `bootstrap.py`: nessuna decisione (`if`, cicli, confronti, operatori booleani, aritmetica, `try`,
  comprehension con filtro), nessuna classe, nessun nome dichiarato a livello di modulo.
- Domain, application e `bootstrap.py` non usano librerie standard tecniche (rete, processi, thread,
  ambiente: `os`, `threading`, `concurrent`, `asyncio`, `socket`, `http`, `urllib`, `ssl`, `subprocess`, ...).
- Domain e application non nominano tecnologie, exchange, fornitori IA o valute di regolamento nei
  testi del codice (docstring escluse).
- Errori: si solleva solo un errore del progetto; un errore si chiama `*Error` e discende da
  `AutotradingError`; nessun `except` generico (`Exception`, `BaseException`, nudo).
- Un caso d'uso per modulo, con il solo metodo pubblico `execute`, nel modulo che porta il suo nome;
  un `*Command` è una dataclass frozen nel modulo del caso d'uso omonimo.
- Una classe pubblica di `adapters/outbound/<tecnologia>/` è un `*Adapter` o un `*Error`.
- Nessuna cartella `common`/`utils`/`shared`; nessun `typing.Any`; un `type: ignore` nomina il codice
  e ha un commento col motivo.
- Configurazione: `os.environ`, `os.getenv` e le librerie di file di configurazione solo in
  `adapters/configuration/`; il `configuration.py` di una cartella lo importa solo il suo
  `composition.py`; `adapters/configuration` lo importano solo `configuration.py`, `composition.py` e
  `bootstrap.py` (eccezione per nome, anche nei contratti di import-linter); nessun costruttore riceve la
  `ConfigurationSource`; in `bootstrap.py` la sorgente va solo alle funzioni `*_adapters` (se ne legge al
  più `environment()`) e nessun testo ha la forma di un nome di variabile.

Ogni regola ha un esempio che la viola e uno conforme. Le violazioni esistenti sono elencate per nome in
`tests/architecture/known_violations.py`, ciascuna con il Bug che la elimina. L'elenco può solo
diminuire: una violazione nuova e una voce non più violata sono entrambe test rossi. Una regola non si
allenta e l'elenco non cresce senza approvazione del proprietario.

## Nomenclatura

| Cosa | Forma | Esempio |
|------|-------|---------|
| Porta | `<Ruolo>Port`, `typing.Protocol` in `application/<contesto>/ports.py` | `ExchangePort` |
| Adapter | `<Tecnologia><Ruolo>Adapter` | `HyperliquidExchangeAdapter` |
| Adapter finto (solo test) | `Fake<Ruolo>Adapter`, `InMemory<Ruolo>Adapter` | `InMemoryAccountRepositoryAdapter` |
| Caso d'uso | `<Verbo><Oggetto>UseCase`, metodo unico `execute` | `RegisterAccountUseCase` |
| Comando | `<Verbo><Oggetto>Command`, dataclass frozen | `RegisterAccountCommand` |
| Errore | `<Fatto>Error`, sottoclasse di un errore tipizzato del progetto | `LeverageAboveMaximumError` |
| Identificativo | `<Entità>Id`, value object | `TenantId`, `AccountId` |
| Modulo | snake_case, nome del tipo principale | `register_account.py` |

## Principi di codice (vincolanti)

- **Solo eccezioni tipizzate del progetto.** Ogni errore sollevato discende da `AutotradingError`.
  Mai `raise` di eccezioni di sistema (`ValueError`, `KeyError`, `RuntimeError`, `Exception`, ...).
- **L'errore dichiara la propria risposta.** `AutotradingError` porta `status_code` (400 se non lo
  ridefinisce), `permanent` (falso se non lo ridefinisce: un errore permanente mette in pausa i flussi,
  R1.2.4) e `details` (dati che la risposta aggiunge al motivo). Ogni errore si definisce nel livello che
  lo solleva e ridefinisce solo ciò che differisce dal padre. Un solo handler centrale per servizio
  risponde in Problem Details (RFC 9457): nessuna mappa da errore a stato fuori dall'errore (ADR 0027).
- **Una traduzione conserva la causa**: `raise <ErroreTipizzato> from error`.
- **Le eccezioni delle librerie** si catturano solo nell'adapter che usa quella libreria e si
  traducono subito nell'errore tipizzato dichiarato dal contratto della porta.
- **Fail fast, early return.** Si valida all'ingresso e si esce subito; niente `else` dopo un `return`
  o un `raise`, niente annidamenti evitabili.
- **try/except solo se indispensabile**: per tradurre un errore di libreria o per una pulizia che un
  context manager non può fare. Mai per nascondere un errore, mai `except Exception`.
- **Una responsabilità per metodo.** Il corpo di un metodo pubblico si legge come una sequenza di
  passi nominati.
- **Nomi auto esplicativi ed espressivi.** Il nome dice l'intenzione; niente abbreviazioni inventate.
- **Commenti solo se indispensabili, e solo per il razionale** (il perché), mai per descrivere cosa
  fa il codice.
- Pochi parametri; SOLID dove cambia una scelta, non citato.
- Una cartella di ruolo contiene solo tipi di quel ruolo. Nessuna cartella `common`/`utils`/`shared`.
- Tipizzazione completa, mypy strict senza `Any` e senza `type: ignore` non motivati.

## Dashboard

Progetto a sé in `dashboard/` (Vite, React, TypeScript `strict`), fuori dall'esagono come `forecaster/`: parla solo
con l'API programmatica di `api` e non ha logica di business che l'API non esponga (ADR 0116). Struttura, librerie e
nomi di [bulletproof-react](https://github.com/alan2207/bulletproof-react): `src/app` ──> `src/features/<funzionalità>`
──> codice condiviso, mai il contrario, nessun import tra funzionalità, nessun barrel file, import assoluti `@/`. Le
cartelle `utils` e simili sono ammesse solo dentro `dashboard/`: la regola sulle cartelle generiche resta per il Python.
Container `dashboard` servito sul percorso `/dashboard` dello stesso nome HTTPS di `api` (ADR 0117); accesso Entra come
SPA con PKCE tramite MSAL, token in `sessionStorage`, autorizzazione solo sull'API (ADR 0118). Controlli come passi dei
job obbligatori esistenti. Dettagli in `.claude/rules/tech-dashboard.md`.

## Multi-tenancy

Ogni dato appartiene a un tenant. Le entità possedute estendono `TenantOwned`; le porte arrivano al
caso d'uso già legate al tenant della richiesta; PostgreSQL applica row level security dentro
l'adapter. Dettagli in `.claude/rules/context-tenancy.md`.

## Test

Unit test per ogni tipo di produzione, scenari Gherkin eseguiti sui casi d'uso con adapter finti,
test di integrazione per ogni adapter contro la tecnologia vera, test architetturale. Ogni prova si
vede rossa prima di diventare verde. Dettagli in `.claude/rules/tests.md`.

## Sicurezza (vincoli del proprietario)

- Mai segreti in variabili d'ambiente: solo file montati in sola lettura.
- Le credenziali dei conti le leggono solo identità di servizio, mai persone: cifrate nel database,
  decifrabili solo dal `worker` (ADR 0007).
- Mai token personali (PAT) per Azure DevOps: solo `az` con l'identità dell'utente, profilo isolato
  (`docs/architecture.md`).
- Il deploy passa sempre dalla pipeline GitHub Actions.

## Decisioni tecniche (ADR)

Ogni decisione tecnica presa da un lavoro vive in `docs/adr/NNNN-titolo.md`: stato, requisiti,
contesto, decisione, alternative scartate, conseguenze. Il Task sulla board cita le ADR del lavoro.
Una ADR accettata non si riscrive: la si sostituisce con una nuova che la dichiara superata.

## Integrazione e rilascio

Flusso TrunkFlow su `main` protetto: solo pull request integrate per squash, con tutti i controlli
superati. Ogni integrazione pubblica un'immagine e la rilascia in dev; lo stesso digest va in prod
con l'approvazione del proprietario. Dettagli in `.claude/rules/ci.md` e `docs/adr/0001`-`0013`.

## Board

Azure DevOps, organizzazione `fianialessandro`, progetto `AutoTrading`, processo Agile. Epic `E<n>`,
Feature `F<n>.<m>`, User Story `R<n>.<m>.<k>`; il tag di ogni elemento è il suo identificativo.

## Indice delle rule

| Rule | Copre |
|------|-------|
| `layer-domain.md` | `src/autotrading/domain/**` |
| `layer-application.md` | `src/autotrading/application/**` |
| `layer-adapters.md` | `src/autotrading/adapters/**`, `src/autotrading/bootstrap.py` |
| `context-tenancy.md` | tutto ciò che riguarda tenant, utenti, isolamento |
| `context-accounts.md` | contesto `accounts` (F0.2) |
| `context-orders.md` | contesto `orders` (F0.3) |
| `context-verification.md` | contesto `verification` (F0.4) |
| `context-flows.md` | contesto `flows` e ciclo decisionale (F1.1, F1.2, F1.5, F1.6, R1.7.1-R1.7.3) |
| `context-sources.md` | contesto `sources` (F1.3) |
| `context-agent.md` | contesto `agent` (F1.4) |
| `context-notifications.md` | contesto `notifications` (F1.8) |
| `tech-fastapi.md` | `adapters/inbound/api/**` |
| `tech-hyperliquid.md` | `adapters/outbound/hyperliquid/**` |
| `tech-libsodium.md` | `adapters/outbound/libsodium/**` |
| `tech-json.md` | `adapters/outbound/json/**` |
| `tech-telegram.md` | `adapters/outbound/telegram/**` |
| `tech-worker.md` | `adapters/outbound/worker/**` |
| `tech-rss.md` | `adapters/outbound/rss/**` |
| `tech-alternative-me.md` | `adapters/outbound/alternative_me/**` |
| `tech-coinmarketcap.md` | `adapters/outbound/coinmarketcap/**` |
| `tech-system-clock.md` | `adapters/outbound/system_clock/**` |
| `tech-litellm.md` | `adapters/outbound/litellm/**` |
| `tech-oidc.md` | `adapters/outbound/oidc/**` |
| `tech-threads.md` | `adapters/outbound/threads/**` |
| `tech-apscheduler.md` | `adapters/outbound/apscheduler/**` |
| `tech-openrouter.md` | `adapters/outbound/openrouter/**` |
| `tech-forecaster.md` | `forecaster/**`, `adapters/outbound/forecaster/**` |
| `tech-dashboard.md` | `dashboard/**` |
| `tech-sqlalchemy.md` | `adapters/outbound/sqlalchemy/**`, `migrations/**` |
| `ci.md` | `.github/**`, `deploy/**`, `tools/**`, `Dockerfile` |
| `tests.md` | `tests/**` |
| `specs.md` | `specs/**` |
