# ADR 0064 — Blocco del flusso su una posizione diversa da quella attesa

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.1, R1.6.2, R1.2.4; Bug 155
- Collegate: ADR 0063 (registro delle operazioni), ADR 0045 (riconciliazione), ADR 0062 (stato attribuito nel ciclo)

## Contesto

Hyperliquid tiene una sola posizione per asset e per conto. Se l'utente compra a mano sullo stesso asset di un
flusso, il ciclo attribuiva al flusso l'intera posizione del conto: agente e controllo del rischio operavano su una
posizione che non era tutta del flusso. La riconciliazione segnalava l'esecuzione non attribuibile, ma il ciclo
proseguiva. Con il registro dell'ADR 0063 ogni flusso conosce la posizione che si aspetta su ogni suo asset.

## Decisione

- **Domain**: `FlowState` porta le posizioni attese dai totali del registro (`expected_positions`);
  `FlowState.position_mismatch()` confronta, per ogni asset del flusso, la posizione del conto con segno (positiva se
  long) con quella attesa e restituisce il primo `PositionMismatch` (asset, attesa, sul conto), in ordine di asset.
- **Ciclo**: `FlowStateFromFlows.read`, all'inizio del ciclo e dopo la riconciliazione del conto, solleva
  `FlowPositionMismatchError` (permanente) con il motivo "posizione X diversa da quella del flusso: attesa A, sul
  conto B". Il ciclo si ferma al passo di lettura dello stato, quindi nessun ordine parte; `FlowPauseFromFlows` mette
  in pausa il solo flusso del ciclo con quel motivo e la notifica (R1.2.4).
- **Solo dopo una riconciliazione riuscita**: se le esecuzioni nuove non si sono potute leggere, il registro può
  essere indietro rispetto all'exchange; il confronto aspetta il ciclo successivo.
- **Fine ciclo**: la lettura dello stato dopo gli ordini (R1.7.1) non confronta: lo stato si registra comunque.
- La ripresa resta all'utente (R1.1.5), dopo aver sistemato la posizione sul conto.

## Alternative scartate

- **Bloccare solo gli ordini sull'asset diverso e lasciare operare il flusso sugli altri**: l'agente riceverebbe
  comunque uno stato del flusso falso, perché la posizione estranea entra nel margine e nel valore del flusso.
- **Attribuire al flusso solo la sua parte della posizione**: l'exchange non separa le posizioni; margine, PnL non
  realizzato e prezzo di liquidazione sono di tutta la posizione.
- **Pausa di tutti i flussi del conto**: la posizione diversa riguarda un asset, che è di un solo flusso (R1.1.2).

## Conseguenze

- Un intervento manuale su un asset di un flusso ferma quel flusso finché l'utente non lo riprende.
- Un'esecuzione che arriva tra la lettura delle esecuzioni e quella delle posizioni può fermare il flusso per una
  differenza che il ciclo successivo non vedrebbe più; è il prezzo di non operare mai su una posizione incerta.
- Dopo il primo avvio di questa versione, un flusso con una posizione aperta da ordini oltre le 10000 esecuzioni
  conservate dall'exchange si ferma con il motivo: la posizione attesa non si può ricostruire.
