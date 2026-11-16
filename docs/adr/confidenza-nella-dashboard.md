# ADR confidenza-nella-dashboard — Confidenza nel dettaglio del ciclo e confidenza minima nell'editor

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.1.4 (457), Task T3.1.4.2 (478)
- Collegate: ADR confidenza-nella-decisione-e-confidenza-minima, ADR piano-di-uscita-nella-dashboard, ADR
  liste-etichetta-valore-che-vanno-a-capo

## Contesto e problema

R3.1.4 chiede la confidenza della decisione nel dettaglio del ciclo; la confidenza minima va impostata
dall'editor del flusso e confrontata tra versioni.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile
  (schede `ViewTabs`, tabella condivisa, riepilogo, grafici di `src/components/charts`), nessun duplicato per pagina.
- Bug 441: righe del confronto in `dashboard/src/features/flow-versions/utils/configuration-rows.ts` legate all'API.

## Opzioni considerate

1. Nel dettaglio del ciclo (`features/cycles`) la decisione mostra «Confidenza 75» nella stessa lista etichetta-valore
   del piano di uscita (ADR piano-di-uscita-nella-dashboard); nell'editor del flusso (`features/flow-editor`) un campo
   numerico facoltativo con i componenti dei campi esistenti; riga nel confronto delle versioni; client OpenAPI
   rigenerato.
2. Un indicatore grafico della confidenza: scartato per ora, non richiesto.

## Esito della decisione

Opzione 1.

Verifica: prova (scenario di R3.1.4 della dashboard, unit test dei componenti).

### Conseguenze

- Nessun componente nuovo.
