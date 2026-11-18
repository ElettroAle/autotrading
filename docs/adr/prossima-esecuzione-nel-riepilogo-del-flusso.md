# ADR prossima-esecuzione-nel-riepilogo-del-flusso — La panoramica del flusso mostra la prossima esecuzione

- Stato: proposta (18 novembre 2026)
- Requisiti: R6.4.8, Task 615; R2.2.2, R1.2.1
- Collegate: ADR 0052 (ancora dei cicli), ADR riepilogo-dei-risultati-nell-api, ADR riepilogo-dei-risultati-nella-dashboard
- Verifica: prova

## Contesto e problema

La scheda del flusso nell'elenco mostra «Prossima esecuzione prevista» (`ListFlowOverviewsUseCase`,
`schedule.next_after(now)`); la panoramica della pagina del flusso no (proprietario, 18/11/2026).

## Fattori decisionali

- Una sola regola per l'istante: la pianificazione del domain già usata dall'elenco, nessuna copia.
- Nessuna logica nella dashboard: l'istante lo dà l'API.

## Decisione

- Il caso d'uso del riepilogo dei risultati del flusso legge la pianificazione con la stessa porta dell'elenco
  (`FlowSummaryPort`/`FlowTimingPort`) e restituisce `next_cycle_at = schedule.next_after(now)` per un flusso attivo,
  `None` altrimenti; la risposta del riepilogo aggiunge `next_cycle_at`, schema e client generato aggiornati. Se il
  calcolo dell'elenco e quello del riepilogo coincidono in un punto del domain, si usa quello, senza duplicarlo.
- Dashboard (`results-summary.tsx`): voce «Prossima esecuzione prevista» con `formatInstant`, assente con `null`,
  come nella scheda del flusso.
- Prove: unit test del caso d'uso (attivo, in pausa, fermo), dell'API e del componente; scenari R6.4.8.

## Alternative scartate

- Leggere l'istante dall'elenco dei flussi nella pagina del flusso: un'altra richiesta e una funzionalità che ne
  importa un'altra.

## Conseguenze

- La panoramica dice quando il flusso deciderà di nuovo.
