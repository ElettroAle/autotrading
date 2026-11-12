# ADR 0062 — Stato attribuito del flusso nel ciclo

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.1, R1.5.3, R1.4.3; Bug 153
- Collegate: ADR 0042 (integrazione dei cicli), 0044 (stato del flusso dall'exchange); sostituisce il calcolo
  provvisorio di `CycleFlow` introdotto con l'ADR 0042

## Contesto

Il ciclo del worker calcolava lo stato del flusso con `CycleFlow`, nato prima di R1.6.1: liquidità come capitale
allocato meno il margine delle posizioni, valore come capitale allocato più il PnL non realizzato. Ignorava il PnL
realizzato e le commissioni del flusso, quindi dopo una perdita il contesto dell'agente e il registro del ciclo
mostravano il capitale pieno, e il controllo del rischio (R1.5.3) approvava aperture il cui margine il flusso non ha
più. Lo stesso concetto era calcolato correttamente da `FlowState.attributed` per `GET /flows/{id}/state` (ADR 0044):
due calcoli dello stesso stato, uno sbagliato.

## Decisione

- **Una sola fonte**: `FlowStateFromFlows.read` costruisce lo stato del ciclo con `ReadFlowStateUseCase`, lo stesso
  caso d'uso dell'API, sulle stesse porte del worker (attività del conto dall'exchange e ordini della piattaforma).
- **`CycleFlow` non calcola**: tiene lo stato attribuito e la lettura del conto. Valore complessivo e rendimento sono
  quelli dello stato attribuito, il rendimento con due decimali.
- **Tetto del conto**: nel ciclo la liquidità disponibile è la minore tra quella attribuita al flusso e il margine
  libero del conto, mai sotto zero. Il margine libero è condiviso con gli altri flussi e con l'operatività manuale:
  un flusso non impegna margine che l'exchange non ha.
- **Dettagli delle posizioni**: lato, leva, prezzo di ingresso e di liquidazione mostrati all'agente restano quelli
  della lettura del conto sugli asset del flusso, che l'attività non riporta.

## Alternative scartate

- **Correggere la formula dentro `CycleFlow`**: resterebbero due calcoli dello stesso stato da tenere allineati.
- **Registro interno dei PnL del flusso**: già scartato dall'ADR 0044; riconsiderato a parte (Bug 154).

## Conseguenze

- A ogni ciclo il worker legge anche l'attività del conto e gli ordini della piattaforma.
- Vale il limite dell'ADR 0044: l'exchange restituisce solo le esecuzioni più recenti.
- Se l'attività del conto non è leggibile, lo stato del flusso non si può attribuire e il ciclo fallisce come per
  un exchange non raggiungibile; il ciclo successivo legge di nuovo.
- La quota delle aperture resta misurata sul capitale allocato (R1.5.1); la liquidità attribuita decide se il
  margine dell'apertura è coperto (R1.5.3).
