# ADR 0056 — Notifiche e chiusure registrate dal ciclo

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.2, R1.7.2, R1.8.2
- Collegate: ADR 0042 (integrazione dei cicli nel worker), 0045 (non attribuibili), 0047 (storico delle posizioni
  chiuse), 0055 (stop di un flusso)

## Contesto

La riconciliazione del conto (R1.6.2), le notifiche essenziali (R1.8.2) e lo storico delle chiusure dell'agente e
di quelle avvenute fuori dalla piattaforma (R1.7.2) esistono come casi d'uso, ma il ciclo del worker non li usa.

## Decisione

- **Porte del ciclo**: `TenantCyclePorts` porta `reconcile_account`, `openings`, `closed_positions` e `notify`.
- **Riconciliazione** nel passo di aggiornamento dello stato, dopo gli ordini: i casi nuovi e le posizioni chiuse
  fuori si notificano; un exchange non raggiungibile si registra nel log e non fa fallire il ciclo.
- **Ordini del ciclo** (`OrdersFromOrders`): apertura eseguita, chiusura eseguita e rifiuto si notificano; una
  chiusura dell'agente entra nello storico con l'apertura del flusso sull'asset e il ciclo che l'ha chiusa. Il valore
  di un'apertura si notifica in unità intere, il PnL come lo riporta l'exchange.
- **Pausa automatica** (`FlowPauseFromFlows`): ogni flusso messo in pausa si notifica con il motivo.
- **Ciclo fallito**: `NotifiedCycles` avvolge il repository dei cicli e notifica il fallimento con il messaggio.
- **Chiusura fuori dalla piattaforma** (`ClosedPositionsFromOpenings`, ponte della porta `ClosedPositionsPort`): la
  posizione entra nello storico dall'ultima apertura del flusso; il prezzo di chiusura è quello che il PnL riportato
  implica. Una chiusura fatta solo da ordini manuali della piattaforma non è "fuori": la registra il comando manuale.

## Alternative scartate

- **Notifiche dentro i casi d'uso dei contesti**: legherebbe `orders` e `flows` al contesto `notifications`.
- **Prezzo di chiusura letto dalle esecuzioni**: le esecuzioni fuori dalla piattaforma possono mancare (liquidazione
  senza fill leggibile), il PnL c'è sempre.

## Conseguenze

- Ogni ciclo legge anche l'attività del conto: una chiamata in più all'exchange per ciclo.
