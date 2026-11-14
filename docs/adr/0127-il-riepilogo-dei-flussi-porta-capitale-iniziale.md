# ADR 0127 — Il riepilogo dei flussi porta capitale iniziale, capitale attuale, rendimento ed esiti recenti

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.2 (Task T2.2.2.1)
- Collegate: R1.7.3 (`GET /flows/overview`), R1.6.1 (stato attribuito del flusso), ADR 0018 (numeri come
  stringhe), ADR 0116, ADR 0119, ADR 0120 (equity per ciclo)

## Contesto e problema

La pagina dei flussi mostra, oltre a ciò che `GET /flows/overview` già restituisce, capitale iniziale, capitale
attuale, rendimento percentuale ed esito degli ultimi 10 cicli. Il rendimento è una regola di business: non si
calcola nel frontend.

## Decisione

- Capitale iniziale = capitale allocato della configurazione corrente; capitale attuale = equity dello stato
  attribuito del flusso (R1.6.1), la stessa grandezza della curva (ADR 0120).
- Value object `FlowReturn` nel dominio `flows`: iniziale, attuale, rendimento percentuale con due decimali, non
  disponibile con capitale iniziale zero.
- `ListFlowOverviewsUseCase` aggiunge al riepilogo lo stato attribuito e gli esiti degli ultimi 10 cicli dalle porte
  del contesto; `FlowOverviewResponse` aggiunge `initial_capital`, `current_capital`, `return_percent` (stringhe) e
  `recent_outcomes` (dal più recente). Esclude bozze e archiviati.
- Frontend: funzionalità `flows`, rendimento verde se positivo e rosso se negativo, esiti come icone con testo
  accessibile.

## Alternative scartate

- **Calcolo nel frontend da `/flows/{id}/state`**: nessun cambio di API, ma la regola del rendimento finisce nel
  frontend e servono N chiamate.

## Conseguenze

- Il riepilogo legge lo stato attribuito di ogni flusso: un costo per flusso a ogni lettura, accettabile con pochi
  flussi.
