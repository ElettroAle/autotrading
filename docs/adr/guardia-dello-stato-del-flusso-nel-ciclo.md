# ADR guardia-dello-stato-del-flusso-nel-ciclo — Guardia dello stato del flusso all'inizio del ciclo

- Stato: accettata (15 novembre 2026)
- Requisiti: Bug 373 (Task 374); R1.2.1, R1.2.2, R1.2.4
- Collegate: ADR 0055, ADR 0062, ADR 0104

## Contesto e problema

Solo il pianificatore del `worker` sa quali flussi sono attivi: ogni ~5 secondi toglie i job dei flussi non più
attivi. `RunCycleUseCase` prende l'istante previsto (`CycleRepositoryPort.claim`), tiene il lock del flusso e fa
girare il grafo senza leggere lo stato del flusso. Un job che scatta tra il cambio di stato e il giro successivo del
pianificatore fa un ciclo completo, ordini compresi, per un flusso in pausa, fermato o archiviato; con uno stop in
corso le posizioni aperte da quel ciclo restano fuori dalla chiusura dello stop, che le ha già lette.

## Fattori decisionali

- Nessun ordine per un flusso che non è attivo quando il ciclo comincia.
- Nessuna notifica o pausa spuria, nessuna voce che l'utente debba interpretare.
- Coerenza con lo stop: lo stato si salva prima di attendere il ciclo in corso (`StopFlowUseCase`, ADR 0055).

## Opzioni considerate

### 1. Pianificatore più frequente

- Pro: nessun codice nel caso d'uso.
- Contro: riduce la finestra senza chiuderla; più carico sul database.

### 2. Errore tipizzato "flusso non attivo" dal primo passo del grafo

- Pro: usa il fail fast esistente.
- Contro: il ciclo risulta fallito, l'utente riceve una notifica di fallimento e lo storico mostra un errore che non
  c'è.

### 3. Ciclo registrato come saltato

- Pro: traccia visibile.
- Contro: "saltato" significa sovrapposizione (R1.2.2); lo storico di un flusso fermato mostrerebbe cicli mai suoi.

### 4. Guardia in `RunCycleUseCase` dentro il lock: flusso non attivo, nessun ciclo

- Pro: chiude la finestra; letto dentro il lock vede anche lo stato salvato da uno stop che aspetta il ciclo; il
  ciclo non diventa né fallito né saltato, come un job mai scattato.
- Contro: una lettura del flusso in più per ciclo; la riga presa da `claim` resta senza esito, quindi invisibile
  nello storico (filtro `RECORDED`).

## Esito della decisione

Opzione 4.

- `CycleGuards` riceve `CycleFlowActivityPort` (`application/flows/ports.py`), che `ReadFlowActivityUseCase` realizza
  sul `FlowRepositoryPort` con `FlowStatus.runs_cycles`: il caso d'uso del ciclo resta generico e non legge il
  flusso intero.
- Dopo `claim`, nel blocco del lock e prima di guardare se il lock è stato preso, il ciclo legge l'attività del
  flusso: se il flusso non è attivo restituisce `None` senza registrare, notificare, mettere in pausa né registrare
  l'equity. Così un flusso fermato mentre il ciclo precedente gira non riceve nemmeno un ciclo saltato.
- Il controllo si fa solo all'inizio: un ciclo già in corso quando il flusso va in pausa o si ferma si conclude e
  invia i suoi ordini, come la versione della configurazione letta all'inizio (R1.1.3); lo stop poi chiude le
  posizioni dopo il ciclo (ADR 0055, scenario di R1.1.5).

È l'unica opzione che chiude la finestra senza inventare un esito nuovo né sporcare lo storico.

## Conseguenze

- Un flusso cancellato non esiste (si archivia), quindi `FlowNotFoundError` non è un caso del ciclo.
- La pausa durante un ciclo non ferma gli ordini di quel ciclo: resta il comportamento documentato.
- Uno scenario di R1.2.1 descrive il ciclo che non parte per un flusso in pausa, fermo o archiviato.
