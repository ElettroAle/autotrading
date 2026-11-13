# ADR 0110 — Outbox delle integrazioni esterne: libreria pronta o tabella propria

- Stato: proposta (13 novembre 2026), in attesa della decisione del proprietario
- Requisiti: RF-24.01, R1.8.2, RNF-03; Task T0.0.2 (178)
- Collegate: ADR 0092 (notifiche come passi espliciti dei casi d'uso), ADR 0089 (un adapter, una tecnologia),
  ADR 0042 (cicli nel worker, lettura del pianificatore fra i tenant), ADR 0022 (ordini con `cloid`)

## Contesto e problema

Il proprietario ha deciso che l'outbox va messo per tutte le integrazioni con sistemi esterni, a partire da Telegram,
ma prima di scriverlo a mano vuole sapere se esiste una libreria pronta che non appesantisca la piattaforma.

Oggi una notifica parte subito: `NotifyUseCase` (`application/notifications/notify.py`) trova la chat del tenant e la
consegna con `MessengerPort` (adapter `telegram/`); se l'invio fallisce lo scrive nel log e la notifica è persa.
Ogni adapter `sqlalchemy/` apre la propria transazione (`engine.begin()`) a ogni chiamata: non c'è un'unità di lavoro
che tenga insieme le scritture di più porte.

Requisiti del Task: scrittura dell'evento nella stessa transazione dell'azione, consegna almeno una volta con
deduplica, ritentativi con backoff, isolamento per tenant (RLS), nessun segreto in variabili d'ambiente, rispetto
delle regole di architettura (un adapter = una tecnologia, il caso d'uso orchestra).

## Criteri

1. Compatibilità con lo stack: Python 3.15, SQLAlchemy 2 sincrono, `psycopg` 3, PostgreSQL 16 ufficiale.
2. Isolamento per tenant con RLS come ogni tabella posseduta.
3. Schema solo in Alembic.
4. Peso: dipendenze nuove, processi o runtime nuovi.
5. Manutenzione e licenza.
6. Esagono: nessuna libreria in domain o application, nessun adapter che orchestra.

## Opzioni valutate

Dati da PyPI al 13 novembre 2026.

| Opzione | Versione, ultimo rilascio | Licenza | Esito sui criteri |
|---|---|---|---|
| `procrastinate` | 3.11.0, 11/11/2026 | MIT | La migliore fra le librerie: `psycopg` 3 (già nostro), extra `sqlalchemy`, `RetryStrategy` con backoff esponenziale, `defer` su una connessione esterna nella stessa transazione (outbox documentato). Contro: tabelle `procrastinate_jobs` globali, senza tenant né RLS; schema con le sue migrazioni SQL; un suo worker con il suo ciclo accanto al nostro; la connessione esterna è documentata per `psycopg` asincrono e per SQLAlchemy con `psycopg2`, da verificare per SQLAlchemy sincrono con `psycopg` 3. Dipendenze nuove: `attrs`, `asgiref`, `croniter`, `packaging`, `typing-extensions` (`psycopg-pool`, `python-dateutil` già presenti). |
| `pgqueuer` | 2.0.0, 09/11/2026 | MIT | Coda su PostgreSQL con LISTEN/NOTIFY, solo asincrona; dipendenze pesanti (`pydantic-settings`, `typer`, `tabulate`, `croniter`, `uvloop`); tabelle globali senza RLS. |
| `faststream-outbox` | 0.21.0, 03/11/2026 | — | Pubblica verso broker (Kafka, RabbitMQ, NATS, Redis) tramite FastStream, con SQLAlchemy asincrono: non consegna a un'API HTTP come Telegram e porta un framework intero. |
| `pgmq` / `tembo-pgmq-python` | 1.1.4, 20/09/2026 | — | Richiede l'estensione `pgmq` di PostgreSQL, assente nell'immagine ufficiale `postgres:16`: immagine del database personalizzata. |
| `python-outbox` | 0.1.8, 14/10/2022 | MIT | Ferma dal 2022, richiede SQLAlchemy < 2 e pydantic < 2: incompatibile. |
| `eventsourcing` | 9.5.6, 13/11/2026 | — | Framework di event sourcing: cambia il modello di persistenza, sproporzionato. |
| Tabella propria | — | — | Una tabella `notifications` (già prevista da `docs/architecture.md:113`: «Eventi notificati, canale, esito») con `tenant_id` e RLS, scritta da un adapter `sqlalchemy/`, consegnata da un caso d'uso nel worker. Nessuna dipendenza nuova; circa una tabella, una migrazione, due casi d'uso, un adapter. |

## Raccomandazione

**Tabella propria**, senza libreria.

- Nessuna libreria soddisfa l'isolamento per tenant: tutte usano tabelle globali che il loro worker legge per intero.
  Per restare dentro RNF-03 bisognerebbe comunque una tabella nostra con RLS e mettere nel job solo il suo
  identificativo: la libreria resterebbe solo come consegnatore con backoff, che sono poche righe.
- `procrastinate` è l'unica candidata seria. Diventa interessante solo se si decide di usarla anche come pianificatore
  dei cicli al posto di APScheduler (prevista da `docs/architecture.md:144` e non ancora presente), perché offre
  anche i task periodici: allora un solo runtime coprirebbe pianificazione e outbox. È una scelta del proprietario.

### Come sarebbe la tabella propria nell'esagono

```text
caso d'uso che agisce ──> Notify<Evento>UseCase ──> NotifyUseCase ──> NotificationOutboxPort.add(notifica)
                                                                        └── SqlAlchemyNotificationOutboxAdapter
                                                                            (tabella notifications, RLS)
worker, a ogni giro ──> DeliverPendingNotificationsUseCase (per tenant)
                          ├── NotificationOutboxPort.pending()
                          ├── MessengerPort.send(chat, testo)        ◄── TelegramMessengerAdapter (invariato)
                          └── NotificationOutboxPort.delivered(id) | failed(id, prossimo tentativo)
```

- Contesto `notifications`: porta `NotificationOutboxPort` in `application/notifications/ports.py` con i suoi
  errori; `NotifyUseCase` registra invece di inviare; nuovo `DeliverPendingNotificationsUseCase` consegna, segna
  l'esito e calcola il prossimo tentativo con backoff esponenziale e un massimo di tentativi.
- Adapter: `SqlAlchemyNotificationOutboxAdapter` in `adapters/outbound/sqlalchemy/`; l'adapter `telegram/` resta
  com'è. Nessun decorator, nessun adapter che riceve porte.
- Il giro del consegnatore legge i tenant con notifiche in attesa come il pianificatore legge i flussi attivi di ogni
  tenant (ADR 0042), poi lavora per tenant con la sessione legata al tenant.
- Deduplica: ogni notifica ha un identificativo; la consegna è almeno una volta. Telegram non ha una chiave di
  idempotenza: un arresto fra l'invio e la marcatura può ripetere un messaggio una volta.
- I chiamanti di ADR 0092 non cambiano: i passi espliciti restano nei casi d'uso.

### Atomicità con l'azione

Il requisito «stessa transazione dell'azione» richiede un'unità di lavoro che oggi non esiste: ogni porta apre la sua
transazione. Due strade, da scegliere:

1. **Outbox durevole subito dopo l'azione** (raccomandata come primo passo): la notifica si scrive appena l'azione è
   salvata. Rimane una finestra minima (arresto fra le due scritture) in cui la notifica può mancare, ma un invio
   fallito non si perde più e viene ritentato.
2. **Unità di lavoro**: una porta che apre una transazione condivisa dalle porte del caso d'uso. Garantisce
   l'atomicità ma tocca tutti gli adapter `sqlalchemy/` e la composizione per tenant: lavoro grande, da motivare con un
   requisito.

## Ambito

- **Telegram**: sì, è l'unica integrazione esterna che produce effetti dopo una scrittura; l'email (RF-24.01, F3)
  userà la stessa tabella con un altro canale.
- **Ordini Hyperliquid**: no. L'ordine è l'azione stessa, non una conseguenza di una scrittura; il ciclo ne ha bisogno
  subito per registrarne l'esito; l'idempotenza c'è già con il `cloid` (ADR 0022) e la riconciliazione. Spostarlo in
  una coda vorrebbe dire ordini piazzati in ritardo, la stessa scelta funzionale lasciata aperta per la ripresa del
  ciclo dopo un riavvio (Bug 183).
- **Modelli IA, fonti, catalogo**: letture, senza effetti da garantire; fuori ambito.

## Conseguenze

- Con la tabella propria: nessuna dipendenza nuova, una migrazione con RLS, una notifica fallita non si perde più, il
  consegnatore gira nel worker esistente.
- Con `procrastinate`: un runtime in più, schema fuori da Alembic da riportare in una migrazione, tabelle globali da
  accettare come scostamento da RNF-03 oppure da usare solo con identificativi.
- In entrambi i casi serve un Task di realizzazione sotto la Feature delle notifiche (F1.8).

## Confronto con le decisioni scritte

- CLAUDE.md:117-120 («prima di un decorator con effetti si valuta l'outbox»): questa ADR è la valutazione; la proposta
  non usa decorator.
- CLAUDE.md:109-116 (un adapter = una tecnologia, librerie solo nella loro cartella): la tabella propria sta in
  `sqlalchemy/`, Telegram resta in `telegram/`.
- CLAUDE.md, Multi-tenancy (ogni dato appartiene a un tenant, RLS nell'adapter) e docs/requirements.md RNF-03: la
  tabella propria li rispetta; le librerie valutate no, senza adattamenti.
- docs/architecture.md:113 (tabella `notifications`: eventi notificati, canale, esito): la tabella propria la realizza.
- docs/architecture.md:144 (APScheduler con job store in PostgreSQL): non ancora presente; citato perché
  `procrastinate` potrebbe sostituirlo, scelta del proprietario.
- ADR 0092 (notifiche come passi espliciti, outbox da valutare a parte): rispettata, i chiamanti non cambiano.
- Scostamenti: nessuno; la decisione finale (introdurre l'outbox, con quale opzione, con o senza unità di lavoro)
  resta al proprietario.
