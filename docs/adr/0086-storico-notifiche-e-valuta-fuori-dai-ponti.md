# ADR 0086 — Storico, notifiche e valuta fuori dai ponti di bootstrap

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.1.5, R1.6.2, R1.7.2, R1.8.2, R0.4.1; Bug 171
- Collegate: ADR 0056 (notifiche e chiusure registrate dal ciclo, di cui supera la parte "ponti"), ADR 0061 (chiusura
  manuale nello storico), ADR 0070 (ogni chiusura notificata una volta), ADR 0055 (ponti dello stop), ADR 0082 (regole
  del ciclo nell'esagono)

## Contesto e problema

I test di architettura (Task 174) vietano decisioni in `bootstrap.py`, che per contratto è solo composition root.
Il Bug 171 raccoglie quelle rimaste nei ponti dello storico, delle notifiche e della valuta:

- **chiusura fuori dalla piattaforma** (`ClosedPositionsFromOpenings`): apertura assente o perdita oltre il valore
  della posizione decidevano fra storico e notifica isolata;
- **ordini del ciclo** (`_follow_order`, `_follow_closing`, `_opening_notification`): rifiuto, ordine senza esito,
  chiusura o apertura; chiusura senza apertura del flusso; valore dell'apertura calcolato e arrotondato all'unità;
- **ordine del flusso dall'esito del rischio** (`_flow_order_of`): `isinstance` fra apertura e chiusura approvate;
- **chiusure dell'API** (`FlowPositionsFromOrders`, `ManualClosingsRecordedInFlows`): errori del worker tradotti in
  rifiuti, esito confermato riconosciuto dai campi presenti;
- **errori degli ordini nella procedura di verifica** (`_result_of`): `try` che rinomina gli errori del contesto
  `orders` in quelli del contesto `verification`;
- **valuta** (`USDC`, `WHOLE_UNIT`): costanti di business nel composition root, scelte senza che l'exchange le
  dichiari.

## Decisione

- **Valuta dichiarata dall'adapter dell'exchange**: la valuta di regolamento è `MARGIN_CURRENCY` dell'adapter
  Hyperliquid, la stessa con cui l'adapter legge saldo e margine. Il composition root la passa a chi compone le
  notifiche (`TenantCyclePorts.settlement_currency`, `NotifiedClosedPositions`, `ClosingNoticeByNotification`);
  nessun altro la scrive.
- **Arrotondamento nel dominio delle notifiche**: `Notification.position_opened` mostra il valore in unità intere;
  `Execution.value` (dominio `orders`) è il valore che l'esecuzione ha messo sul mercato.
- **Chiusure nello storico in `application/flows`**: `RecordFlowClosingUseCase` (chiusura di un ciclo) e
  `RecordOutsideClosingUseCase` (chiusura fuori dalla piattaforma, con i due avvisi nel log) decidono fra storico e
  notifica isolata; la notifica isolata passa dalla porta `ClosingNoticePort`. `RecordManualClosingUseCase` riceve
  il fill della chiusura manuale anche quando manca e non registra nulla.
- **Ordini del ciclo in `application/orders`**: `FollowFlowOrdersUseCase` dice, per ogni ordine, se è un rifiuto,
  un'apertura o una chiusura, attraverso la porta `FlowOrderEventsPort`; il ponte `FlowOrderEvents` traduce ogni
  evento in notifica o in comando dello storico.
- **Chiusura dell'API come dato**: `CloseFlowPositionUseCase` (`application/orders`) chiude attraverso il worker e
  restituisce `ClosingReport` invece di sollevare. `ClosingFill.reported` e `PositionClosing.reported` (dominio
  `flows`) costruiscono il fill solo se confermato e la chiusura del flusso, `None` se non c'era posizione.
- **Ordine del flusso costruito dall'esito**: `ApprovedOpening.order_with` e `ApprovedClose.order_with` ricevono i
  due costruttori e usano il proprio; il contesto `flows` non importa `orders`.
- **Errori degli ordini nominati da chi chiede**: `answered_or_named` (`application/orders/order_failures.py`) sa
  quale errore del contesto `orders` è un conto non trovato; chi chiede passa come il proprio contesto nomina quel
  caso e ogni altro, e la causa resta (`raise ... from`).
- I ponti restano traduzione: costruiscono comandi e notifiche, senza condizioni.

## Alternative scartate

- **Porta della valuta interrogata a ogni notifica**: l'installazione ha un solo exchange e la valuta è un fatto
  della sua tecnologia, non un dato che cambia; una porta aggiungerebbe una lettura senza informazione. Un secondo
  exchange la renderà un dato del conto.
- **Ponti spostati in una cartella di adapter "in-process"**: nuova tecnologia nell'esagono, decisione del
  proprietario; e le regole resterebbero fuori da `domain` e `application`.
- **Mappa di tipi per `_flow_order_of`**: nasconde la stessa scelta in una tabella del composition root.
- **Errore "conto non trovato" comune nella radice degli errori**: cambierebbe la gerarchia del progetto per un solo
  caso di traduzione.

## Conseguenze

- Una notifica nuova con un importo prende la valuta dal composition root, mai da una costante.
- Un nuovo esito di un ordine del flusso si aggiunge a `FollowFlowOrdersUseCase` e alla sua porta.
- Il comportamento verso l'utente non cambia: stessi testi, stessi importi, stessi casi senza storico.
- Restano nell'elenco delle violazioni note solo le voci dei Bug 170, 173 e 175.
