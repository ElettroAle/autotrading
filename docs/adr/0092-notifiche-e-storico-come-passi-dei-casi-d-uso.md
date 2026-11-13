# ADR 0092 — Notifiche e storico delle chiusure come passi espliciti dei casi d'uso

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.1.5, R1.6.2, R1.7.2, R1.8.2; Bug B0.0.3 (177)
- Supera: le parti di ADR 0086 che affidano a classi di `bootstrap.py` la notifica delle chiusure
  (`NotifiedClosedPositions`, `ClosingNoticeByNotification`) e la traduzione degli eventi degli ordini
  (`FlowOrderEvents`); la parte «ponte» di ADR 0061 (`ManualClosingsRecordedInFlows`)
- Collegate: ADR 0089 (un adapter, una tecnologia; niente ponti), ADR 0088 (porte del consumatore realizzate da casi
  d'uso), ADR 0056 e 0070 (ogni chiusura notificata una volta), CLAUDE.md (Regola delle dipendenze, Nomenclatura)

## Contesto e problema

Dopo ADR 0089 restavano in `bootstrap.py` sette classi elencate fra le violazioni note del Bug 177:

- due decorator veri di `ClosedPositionRepositoryPort` e `PositionClosingPort`: `NotifiedClosedPositions` (ogni
  posizione aggiunta allo storico veniva anche notificata) e `ManualClosingsRecordedInFlows` (ogni chiusura manuale
  veniva anche registrata nello storico del flusso);
- cinque ponti: `PausedFlowNotices`, `CycleFailureNotices`, `ClosingNoticeByNotification`, `OutsideClosingsInHistory`
  e `FlowOrderEvents`, che realizzavano la porta di un contesto chiamando la notifica o lo storico di un altro.

Un decorator che aggiunge un effetto verso un sistema esterno (il bot Telegram) andrebbe valutato insieme all'outbox;
il proprietario ha chiesto di risolvere ora con le regole di CLAUDE.md e di valutare l'outbox a parte.

## Decisione

- **Il passo successivo lo fa il caso d'uso che agisce.** Chi registra una chiusura nello storico la notifica subito
  dopo (`RecordFlowClosingUseCase`, `RecordOutsideClosingUseCase`, `RecordManualClosingUseCase`, `StopFlowUseCase`);
  `ClosePositionUseCase` (contesto `orders`) chiude e poi passa l'esito allo storico dei flussi.
- **Ogni notifica è un caso d'uso del contesto `notifications`**: `NotifyFlowPausedUseCase`, `NotifyCycleFailedUseCase`,
  `NotifyOrderRejectedUseCase`, `NotifyPositionOpenedUseCase`, `NotifyPositionClosedUseCase`. Compongono il testo con
  `Notification` e lo consegnano con `NotifierPort`; la valuta di regolamento arriva dal composition root come prima.
- **Porte del consumatore realizzate da casi d'uso** (come in ADR 0088): `flows` dichiara `FlowPausedNoticePort`,
  `CycleFailedNoticePort`, `PositionClosedNoticePort`, `OutsideClosingRecorderPort`; `orders` dichiara
  `OrderRejectedNoticePort`, `PositionOpenedNoticePort`, `FlowClosingRecorderPort`, `ManualClosingRecorderPort`;
  `cycles` dichiara `CycleFailureNoticePort`. Ognuna ha la forma `execute(...)` del caso d'uso che la realizza.
- **I dati di un fill attraversano i contesti per struttura**: `flows` dichiara `ExecutedFillPort` e
  `ReportedFillPort` (prezzo medio, istante, commissione, PnL realizzato), soddisfatte da `Execution` e
  `OrderOutcome` di `orders` senza che `flows` importi `orders`.
- **Il fallimento di un ciclo raggiunge il tenant giusto** con `TellCycleFailureUseCase` (contesto `cycles`): trova il
  tenant del flusso (`FlowTenantPort`) e passa al caso d'uso di quel tenant, come `RecordActualPricesOfTenantsUseCase`.
- **`FollowFlowOrdersUseCase`** riceve i tre seguiti di un ordine (`FlowOrderFollowers`: rifiuto, apertura,
  chiusura) e il nome del flusso nel comando; il ponte che traduceva gli eventi sparisce.
- `bootstrap.py` istanzia e collega soltanto; le sette voci escono da `tests/architecture/known_violations.py`.
- Comportamento invariato: stessi testi, stesso PnL; un errore di consegna della notifica resta registrato nel log
  da `NotifyUseCase` senza fermare l'azione.

## Alternative scartate

- **Tenere i decorator di notifica**: aggiungono un effetto verso un sistema esterno nascosto dietro la porta del
  repository; senza outbox una notifica può andare persa o partire per una scrittura poi annullata, e chi legge il
  caso d'uso non vede il passo.
- **Introdurre subito l'outbox**: il proprietario vuole prima valutare librerie pronte, per non appesantire la
  piattaforma; resta un Task di valutazione separato.
- **Passare `Execution` e `OrderOutcome` alle porte di `flows`**: `flows` dipenderebbe da `orders`, contro la regola
  delle dipendenze fra contesti.

## Conseguenze

- Ogni nuova notifica è un caso d'uso di `notifications` con il suo test del testo; il contesto che la chiede dichiara
  la propria porta.
- L'ordine «prima lo storico, poi la notifica» è scritto nei casi d'uso ed è verificato dai loro unit test.
- L'outbox per Telegram e le altre integrazioni esterne resta da valutare nel Task dedicato; quando arriverà
  sostituirà la consegna diretta dietro `NotifierPort` senza toccare i casi d'uso.
