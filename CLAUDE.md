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
Alembic, PostgreSQL 16, PyNaCl (libsodium), SDK ufficiale Hyperliquid, Entra ID. Dettagli e motivazioni in
`docs/architecture.md`.

## Architettura target

### Container (installazioni `dev` e `prod`, OVH Public Cloud, Docker Compose)

```text
Utente (tailnet) ──HTTPS──> Tailscale Serve ──> api (FastAPI) ──┬──> PostgreSQL (credenziali cifrate, chiave pubblica)
                                            ├──> Hyperliquid (internet)
                                            └──> Entra ID (validazione token)
worker (chiave privata) ──> PostgreSQL, Hyperliquid
fasi successive: forecaster (Prophet), litellm, dashboard
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
  application/                  livello 2: casi d'uso e porte
    errors.py                   ApplicationError
    <contesto>/
      ports.py                  *Port (typing.Protocol)
      errors.py                 errori di application e dei contratti delle porte
      <verbo>_<oggetto>.py      un caso d'uso per modulo
  adapters/                     livello 3: tecnologie, ognuna incapsulata
    inbound/api/                FastAPI
    outbound/<tecnologia>/      hyperliquid/, libsodium/, sqlalchemy/
  bootstrap.py                  composition root
tests/                          vedi .claude/rules/tests.md
specs/                          vedi .claude/rules/specs.md
tools/                          script Python della pipeline, fuori dall'esagono (.claude/rules/ci.md)
deploy/                         cloud-init, compose e policy Tailscale delle installazioni
.github/                        workflow e action della pipeline TrunkFlow
docs/adr/                       decisioni tecniche, una per file
```

**Contesti** = aree di logica di business, non tecnologie. In E0: `tenancy`, `accounts`, `orders`,
`verification`. Un contesto nuovo nasce solo con decisione del proprietario e porta con sé la propria
rule `context-<nome>.md`.

**Comunicazione tra contesti**: chiamata in-process attraverso porte o casi d'uso esposti. Eventi solo
se un singolo design li motiva, con decisione del proprietario.

## Regola delle dipendenze

Le dipendenze puntano solo verso il centro: `adapters` ──> `application` ──> `domain`. Mai il contrario.

- `domain` non importa nulla di `application`, `adapters`, `bootstrap`, né librerie esterne.
- `application` importa solo `domain` e la libreria standard.
- Le librerie tecnologiche si importano solo nella cartella del loro adapter.
- Le cartelle `adapters/outbound/<tecnologia>` non si importano a vicenda.
- `domain/tenancy` è l'unico contesto che tutti gli altri contesti possono importare.

Verificato da import-linter (contratti in `pyproject.toml`), eseguito da `tests/architecture/`.
Un contratto non si allenta e non si aggiunge un `ignore_imports` senza approvazione del proprietario.

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
| `tech-fastapi.md` | `adapters/inbound/api/**` |
| `tech-hyperliquid.md` | `adapters/outbound/hyperliquid/**` |
| `tech-libsodium.md` | `adapters/outbound/libsodium/**` |
| `tech-sqlalchemy.md` | `adapters/outbound/sqlalchemy/**`, `migrations/**` |
| `ci.md` | `.github/**`, `deploy/**`, `tools/**`, `Dockerfile` |
| `tests.md` | `tests/**` |
| `specs.md` | `specs/**` |
