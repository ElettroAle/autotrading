# ADR outbox-delle-integrazioni-esterne-con-procrastinate — Outbox delle integrazioni esterne con procrastinate

- Stato: accettata (15 novembre 2026), decisione del proprietario; numero di tentativi sostituito dall'ADR
  ritentativi-dell-outbox-in-circa-sei-ore
- Requisiti: Task T6.1.1 (377), Task 178; RF-24.01, R1.8.2, RNF-03
- Collegate: sostituisce ADR 0110 (proposta, mai accettata); ADR 0092 (notifiche come passi espliciti dei casi d'uso),
  ADR 0089 (un adapter, una tecnologia), ADR 0104 (checkpointer di LangGraph nella cartella PostgreSQL), ADR 0112
  (APScheduler nel worker), ADR 0022 (ordini con `cloid`)

## Contesto e problema

Oggi un messaggio verso un sistema esterno parte subito: `NotifyUseCase` lo consegna con `MessengerPort` (adapter
`telegram/`); se l'invio fallisce lo scrive nel log e il messaggio è perso. Il proprietario vuole un outbox per tutte
le integrazioni esterne che producono effetti dopo una scrittura (oggi Telegram, poi l'email di E3 e le future), con
una libreria pronta e non scritto a mano. L'ADR 0110 ha confrontato le librerie; restava aperta la scelta.

## Fattori decisionali

- Decisioni del proprietario (15/11/2026): libreria `procrastinate`, nella variante con il solo identificativo del
  messaggio nella coda; outbox generico per integrazione; ordini Hyperliquid fuori dall'outbox.
- `.claude/rules/tech-sqlalchemy.md:17`: ogni tabella di dati posseduti ha `tenant_id` e policy RLS forzata.
- `CLAUDE.md`, regola delle dipendenze: tecnologia = sistema integrato, non la libreria che lo raggiunge; un adapter
  non orchestra e non riceve casi d'uso; una libreria appartiene a una sola cartella.
- Precedente: il checkpointer di LangGraph su PostgreSQL vive in `adapters/outbound/sqlalchemy/` (ADR 0104); lo
  scheduler APScheduler esegue job il cui contenuto decide il caso d'uso (ADR 0112).
- Documentazione di `procrastinate` 3.x: `defer` su una connessione esterna nella stessa transazione
  (`SyncPsycopgConnector` con una `psycopg.Connection`), `RetryStrategy` con backoff esponenziale e numero massimo di
  tentativi; schema SQL fornito dalla libreria, da applicare con il proprio strumento di migrazione.

## Opzioni considerate

### 1. procrastinate con il solo identificativo nella coda, tabella `outbox_messages` con RLS

- Pro: i dati del tenant restano sotto RLS; coda, worker, ritentativi e backoff dalla libreria; accodamento atomico con
  la scrittura del messaggio.
- Contro: schema della libreria da portare in Alembic; un worker della libreria nel processo `worker`.

### 2. procrastinate con il messaggio intero nella coda

- Pro: una tabella in meno.
- Contro: testo e destinatari di tutti i tenant in una tabella senza RLS, scostamento da `tech-sqlalchemy.md:17`.

### 3. Tabella e consegnatore scritti a mano (raccomandazione dell'ADR 0110)

- Pro: nessuna dipendenza.
- Contro: rifiutata dal proprietario: coda e ritentativi scritti a mano.

## Esito della decisione

Opzione 1.

- **Dove vive**: `procrastinate` è un modo di usare PostgreSQL, quindi sta in `adapters/outbound/sqlalchemy/` come il
  checkpointer di LangGraph; la cartella dichiara `procrastinate` tra le sue librerie.
- **Contesto**: l'outbox è del contesto `notifications`, che oggi contiene le integrazioni di consegna. Porta
  `OutboxPort` in `application/notifications/ports.py`:
  - `enqueue(message)`: scrive in `outbox_messages` (`tenant_id`, integrazione, payload JSON, stato, tentativi,
    istanti, ultimo errore) e accoda con `procrastinate` il solo id del messaggio, sulla stessa connessione e nella
    stessa transazione (driver `psycopg` sotto la connessione SQLAlchemy).
  - `process(deliver)`: avvia il worker di `procrastinate`; per ogni id letto, carica il messaggio con la sessione del
    suo tenant (RLS) e chiama la funzione `deliver` ricevuta dal caso d'uso, come lo scheduler esegue i job del
    caso d'uso (ADR 0112). L'adapter non conosce le integrazioni.
- **Casi d'uso**: `NotifyUseCase` accoda invece di inviare. `DeliverOutboxMessageUseCase` sceglie la porta per
  integrazione (`telegram` ──> `MessengerPort`; le prossime con la loro porta) e consegna; un errore transitorio
  della porta torna all'adapter, che ritenta; un errore permanente segna il messaggio come fallito senza ritentare.
- **Ritentativi**: backoff esponenziale con base 5 secondi, al massimo 8 tentativi (circa 6 ore); poi stato
  `fallito`, conservato e visibile nel log.
- **Atomicità con l'azione**: il messaggio si accoda subito dopo l'azione che lo genera, come proponeva l'ADR 0110
  (nessuna unità di lavoro condivisa tra le porte); una consegna fallita non si perde più. Consegna almeno una volta:
  un arresto tra invio e marcatura può ripetere un messaggio.
- **Schema**: lo schema di `procrastinate` e la tabella `outbox_messages` entrano in una migrazione Alembic; un test
  di integrazione verifica che lo schema applicato sia quello della versione installata della libreria.
- **Ambito**: Telegram ora; email e ogni integrazione futura con un effetto dopo una scrittura passano dall'outbox.
  Fuori: ordini all'exchange (l'ordine è l'azione stessa, il ciclo ne registra subito l'esito, idempotenza con
  `cloid` e riconciliazione), letture di modelli IA e fonti.
- Il campanello (R6.2.1) ha la sua tabella `notifications`, dato dell'utente; una notifica scrive lì e accoda nell'
  outbox il messaggio Telegram.

Verifica: prova (test di architettura: `procrastinate` importato solo in `adapters/outbound/sqlalchemy/`; test di
integrazione su PostgreSQL vero: accodamento e messaggio nella stessa transazione, rollback che non lascia né l'uno né
l'altro, RLS sulla tabella `outbox_messages`, ritentativo dopo un errore transitorio, nessun ritentativo dopo un errore
permanente).

### Conseguenze

- Una notifica Telegram non si perde più per un errore di rete; si ritenta per circa 6 ore.
- Una nuova integrazione esterna si aggiunge con la sua porta e il suo nome di integrazione, senza toccare la coda.
- Un runtime in più nel `worker` (il worker di `procrastinate`), sotto il limite di memoria dell'ADR 0165.
- L'ADR 0110 risulta sostituita.
