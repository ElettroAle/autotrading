# ADR scheda-decisioni-nella-pagina-del-flusso — Scheda Decisioni nella pagina del flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.5 (Task 526)
- Collegate: ADR storico-delle-decisioni-nell-api, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune, ADR
  schede-con-aspetto-e-ruolo-di-schede, ADR tabella-condivisa-senza-sforamento-e-con-filtri, ADR
  icone-condivise-di-azioni-e-direzioni, ADR riquadro-dell-ultima-decisione-nella-panoramica (`shorten-text`), ADR 0116

## Contesto e problema

La pagina del flusso ha le schede Panoramica, Posizioni chiuse e Cicli sotto un periodo comune (R6.4.3). Lo storico
delle decisioni deve seguire lo stesso periodo, filtrarsi per asset, azione e direzione e portare al dettaglio del
ciclo.

## Fattori decisionali

- Direttiva del proprietario (16/11/2026): regole architetturali e componenti riusabili.
  - Schede con `ViewTabs`.
  - Tabella, filtri e pagine con `DataTable`, `TableFilters` e `Pagination` di `src/components/ui`.
  - Periodo con `usePeriod`.
  - Azione e direzione con `ActionLabel` e `DirectionLabel`.
  - Ragionamento accorciato con `src/utils/shorten-text.ts`.
- `.claude/rules/tech-dashboard.md`: scheda, periodo e filtri nell'indirizzo; nessun import tra funzionalità.
- R6.4.3 elenca le schede: aggiungerne una cambia il suo testo.

## Opzioni considerate

1. **Quarta scheda «Decisioni» con la funzionalità `features/decisions`.**
   - `api/list-decisions.ts`: query TanStack con periodo, filtri e pagina nella chiave; risposta validata da Zod.
   - `components/decisions-table.tsx`: colonne istante, asset, azione, direzione, confidenza e ragionamento
     accorciato. La riga porta al dettaglio del ciclo.
   - La rotta del flusso aggiunge la scheda «Decisioni» dopo «Cicli».
   - Nello stesso lavoro la narrativa di R6.4.3, nel `.feature` e sulla board, elenca la scheda nuova.
2. **Pagina separata dalla pagina del flusso**: scartata, perché perderebbe il periodo comune che R6.5.5 chiede.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test della tabella: righe, filtri nell'indirizzo, stato vuoto, collegamento.
- Scenari Playwright di R6.5.5 con i finti MSW, che ricevono la rotta.

### Conseguenze

- Il testo di R6.4.3 cambia per elencare la scheda Decisioni.
