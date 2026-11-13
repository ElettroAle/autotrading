# ADR 0082 — Regole del ciclo nell'esagono e porte dei cicli tipizzate

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.2.4, R1.3.7, R1.6.1, R1.6.2, R1.7.3, R0.4.1; Bug 170
- Collegate: ADR 0042 (integrazione dei cicli nel worker, di cui supera la parte "porte opache"), ADR 0041 (ciclo
  dietro porte), ADR 0062 (stato attribuito al flusso), ADR 0064 e 0075 (pausa per differenza confermata), ADR 0069
  (inizio del flusso)

## Contesto e problema

L'audit di architettura ha trovato regole di business nei ponti di `bootstrap.py`, che per contratto è solo
composition root: i ponti traducono fra contesti, non decidono. Le regole trovate:

- **liquidità usabile nel ciclo** (`CycleFlow`): minimo fra liquidità attribuita al flusso e margine libero del conto,
  mai negativa; rendimento arrotondato a due decimali; posizioni del conto filtrate sugli asset del flusso;
- **politica di inizio ciclo** (`FlowStateFromFlows`): riconciliazione tollerante, confronto delle posizioni solo dopo
  una riconciliazione riuscita, seconda riconciliazione prima della pausa (ADR 0075), inizio del flusso dalla prima
  partenza o, se manca, dall'ancora;
- **ambito della pausa** (`FlowPauseFromFlows`): una catena di `isinstance` decideva se l'errore riguarda un conto o
  un fornitore;
- **flusso che tiene un asset** (`AccountReadingFromAccounts.flow_on`): solo un flusso attivo o in pausa blocca la
  procedura di verifica sui suoi asset;
- **pianificazione solo per i flussi attivi** (`_summary_of`);
- **notizie assenti come dato** (`_nothing_collected`, R1.3.7).

Inoltre le porte dei cicli (ADR 0041, 0042) passano `object` opachi: ogni ponte recupera il tipo con `isinstance`
e solleva `FlowOfCycleNotFoundError` se non lo trova, un controllo che il type checker potrebbe fare al posto loro.

## Decisione

- **Fondi del ciclo nel dominio**: `domain/flows/cycle_funds.py`, value object `CycleFunds(attributed, free_margin)`
  con liquidità usabile, valore totale e rendimento. `FlowConfiguration.covers(asset)` dice quali posizioni sono del
  flusso; `CycleFlow` resta il contenitore dei dati letti a inizio ciclo e delega le grandezze a `CycleFunds`.
- **Inizio ciclo in application/flows**: `ReconcileAccountForCycleUseCase` riconcilia il conto, notifica i casi
  nuovi attraverso `UnattributableNoticePort` e dice se la riconciliazione è riuscita (un exchange irraggiungibile
  lascia operare i flussi). `ReadCycleFlowStateUseCase(flow_id, reconciled)` legge lo stato attribuito, confronta le
  posizioni solo dopo una riconciliazione, riconcilia di nuovo prima di sollevare `FlowPositionMismatchError` e
  solleva `FlowExchangeUnavailableError` se la seconda riconciliazione non riesce. `flow_beginning` in
  `domain/flows/flow_timing.py` decide l'inizio del flusso. Il ponte legge lo stato del conto fra le due chiamate,
  come prima, così l'ordine delle letture e degli errori resta lo stesso.
- **Errori con ambito dichiarato**: `AutotradingError.scope` restituisce un `ErrorScope(account_id, provider)`, vuoto
  per default. Gli errori della chiave del fornitore dichiarano il fornitore; credenziali rifiutate e registro
  incompleto dichiarano il conto (`FlowCredentialsRejectedError` riceve l'id del conto).
  `PauseAffectedFlowsCommand.of_error` costruisce il comando dall'ambito; il ponte non conosce più i tipi di errore.
- **Predicati di dominio**: `Flow.holds(account_id, asset)` per la procedura di verifica; `FlowStatus.runs_cycles`
  e `CycleSchedule.planned(runs_cycles, anchor, interval)` per la consultazione dei cicli.
- **Silenzio di una fonte come dato**: `SourceDefinition.silence` dichiara la nota che l'agente riceve quando la
  fonte non raccoglie nulla; `NEWS` la dichiara con `no_recent_news`. `CollectSourceUseCase` la mette in
  `CollectedSource.note`, che non si registra come valore raccolto; il ponte la traduce in `SourceData`.
- **Porte dei cicli generiche**: `FlowSnapshot`, `SourceRequest`, `SourceReading`, `RiskReview` e le porte
  `FlowStatePort`, `SourcePort`, `ContextPort`, `AgentPort`, `RiskPort`, `OrderPort` sono generiche sui tipi che i
  contesti si scambiano (stato del flusso, dati delle fonti, contesto, decisioni, ordini, esecuzioni);
  `RunCycleUseCase` e `RunDueCyclesUseCase` le ricevono con i tipi legati dal composition root. Il contesto
  `cycles` continua a non importare gli altri contesti; i ponti non recuperano più i tipi con `isinstance`.

## Alternative scartate

- **Tipi concreti dei contesti nelle porte dei cicli**: `application/cycles` dovrebbe importare `flows`, `agent` e
  `orders`, contro il contratto di indipendenza dei contesti.
- **Liquidità come metodo di `FlowState`**: il margine libero è un dato del conto, non del flusso; un value object
  del ciclo rende esplicito che il limite viene da fuori.
- **Nota delle notizie come valore restituito da `ReadNewsUseCase`**: diventerebbe un valore registrato del ciclo
  (R1.3.8) con un istante di riferimento inventato.
- **Ambito della pausa deciso da `PauseAffectedFlowsUseCase` per tipo di errore**: il contesto `flows` dovrebbe
  importare gli errori del contesto `agent`.

## Conseguenze

- Ogni errore permanente nuovo che riguarda un conto o un fornitore dichiara il suo ambito; senza dichiarazione va
  in pausa solo il flusso del ciclo.
- Una fonte nuova il cui silenzio è un dato dichiara la sua nota nel catalogo, senza toccare i ponti.
- I ponti dei cicli restano traduzione: le regole hanno unit test di dominio e di application.
