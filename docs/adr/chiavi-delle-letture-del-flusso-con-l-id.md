# ADR chiavi-delle-letture-del-flusso-con-l-id — Ogni lettura di un flusso ha l'id del flusso nella chiave

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 574, Task 575; R6.5.2 (ciclo su richiesta)
- Collegate: ADR chiavi-di-cache-distinte-per-le-letture-dei-conti
- Verifica: prova

## Contesto e problema

Alla fine di «Esegui ora» (`features/flow-commands/api/run-cycle-now.ts:15`) si invalidano le query con
`queryKey[0] === 'flows' || queryKey.includes(flowId)`. La curva del capitale usa `['flow-equity', path]`
(`get-flow-equity.ts:31-33`) e il confronto `['compared-equity', path]`: l'id del flusso è dentro il percorso, non un
elemento della chiave, e il grafico non si aggiorna.

## Fattori decisionali

- Bug 574: a ciclo concluso grafico, ultima decisione e dati del flusso si aggiornano subito.
- Una sola regola per tutte le letture del flusso, verificata da una prova, invece di un elenco di chiavi nel comando.

## Decisione

- Ogni lettura legata a un flusso ha l'id del flusso come elemento della chiave (`['flow-equity', flowId, path]`; il
  confronto mette ogni id confrontato come elemento). L'invalidazione di «Esegui ora» resta per elemento.
- Prova: test che esegue «Esegui ora» e verifica il nuovo caricamento della curva del capitale; test che le chiavi
  delle letture del flusso contengono l'id.

## Alternative scartate

- Invalidare tutte le query: ricarica pagine non toccate.

## Conseguenze

- Una lettura nuova di un flusso senza id nella chiave fa fallire la prova.
