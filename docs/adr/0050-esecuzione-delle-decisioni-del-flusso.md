# ADR 0050 — Esecuzione delle decisioni del flusso nel contesto orders

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.5.5 (Task T1.5.5.1)

## Contesto

Le decisioni approvate dal rischio (ADR 0040) diventano ordini sul conto del flusso: prima le chiusure, poi le
aperture; ogni ordine porta l'identificativo della piattaforma (R0.3.1), è collegato al flusso, al ciclo e alla
decisione, e si registra con l'esito reale letto dall'exchange (R0.3.4). Un rifiuto dell'exchange si registra con
il messaggio originale (R0.3.3) e non ferma gli altri ordini; un exchange che non risponde fa fallire il ciclo
(R1.2.3). Il ciclo (ADR 0041) esegue gli ordini con la porta `OrderPort`, un ordine alla volta, nell'ordine che il
rischio gli consegna. Il contesto `orders` sa già aprire una posizione al prezzo di mercato e chiuderla per intero
(`OpenPositionUseCase`, `CloseExchangePositionUseCase`), e `flows` non può importare `orders` (ADR 0026).

## Opzioni considerate

### 1. Caso d'uso di `orders` che esegue tutti gli ordini del ciclo, con l'ordine di invio nel domain

- Pro: la regola "prima le chiusure" è del domain di `orders` e si prova da sola; un solo accesso al conto per
  ciclo; il rifiuto di un ordine resta un esito, come in E0.
- Contro: `OrderPort` del ciclo riceve la lista degli ordini invece di un ordine alla volta.

### 2. Un ordine alla volta, ordinato dal ponte del rischio in `bootstrap.py`

- Pro: nessuna modifica alla porta del ciclo.
- Contro: una regola di business nel composition root, provata solo dall'integrazione.

### 3. Riuso diretto dei casi d'uso di E0

- Pro: nessun codice nuovo.
- Contro: non collegano l'ordine al flusso; un rifiuto della leva interrompe il ciclo invece di registrarsi.

## Esito della decisione

Scelta: **opzione 1**.

- Domain `orders`: `FlowOpening` (asset, direzione, valore, leva) e `FlowClosing` (asset), il tipo `FlowOrder` e
  `in_sending_order(ordini)`, che mette le chiusure prima delle aperture conservando l'ordine relativo.
- `FlowLink(flusso, istante pianificato del ciclo, asset della decisione)`: il ciclo è identificato dal flusso e
  dal suo istante pianificato, unico per costruzione (ADR 0041); la decisione dall'asset, perché un ciclo ha al più
  una decisione per asset (ADR 0038). `OrderSource` acquista l'origine `flusso` e il collegamento.
- `ExecuteFlowOrdersUseCase` (worker): apre l'accesso al conto una volta, invia gli ordini in sequenza con la
  stessa regola di E0 (un solo invio, rifiuto come esito, ordine senza conferma cercato per identificativo) e
  registra ciascuno appena eseguito. Un rifiuto della leva diventa un ordine rifiutato con il messaggio
  dell'exchange; una chiusura senza posizione sull'exchange non invia nulla, perché non c'è niente da chiudere.
  `OrderExchangeUnavailableError` interrompe gli ordini rimanenti e fa fallire il ciclo; gli ordini già inviati
  restano registrati.
- `OrderPort.execute(flusso, istante, ordini)` riceve gli ordini del ciclo e restituisce gli esiti.
- Tabella `orders`: colonne `flow_id`, `cycle_planned_at`, `decision_asset`, nulle per gli ordini della procedura
  di verifica e dei comandi manuali (migrazione additiva).

### Conseguenze

- Il ponte del ciclo in `bootstrap.py` traduce `ApprovedOpening`/`ApprovedClose` in `FlowOpening`/`FlowClosing`
  e lega il caso d'uso al conto del flusso (integrazione dei cicli).
- Gli scenari di R1.5.5 sono verdi sul caso d'uso con adapter finti.
