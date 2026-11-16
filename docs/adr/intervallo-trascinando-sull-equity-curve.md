# ADR intervallo-trascinando-sull-equity-curve — Intervallo scelto trascinando sull'equity curve

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.3 (421), Task T6.4.3.2 (423)
- Collegate: ADR 0121 (grafici con Recharts), ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune

## Contesto e problema

Il periodo si sceglie solo dal menu; il proprietario vuole scegliere un intervallo da-a trascinando sul grafico,
anche dal telefono (16/11/2026).

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile (schede `ViewTabs`, tabella condivisa, riepilogo, grafici di `src/components/charts`), nessun duplicato per pagina.
- ADR 0121: Recharts è l'unica libreria dei grafici, usata solo dai grafici condivisi di `src/components/charts`.
- R6.4.3: intervallo con etichetta e comando per toglierlo, nell'indirizzo; anche col dito.

## Opzioni considerate

1. Selezione sul grafico condiviso con gli eventi del puntatore (mouse e tocco) e un'area evidenziata
   (`ReferenceArea`) durante il trascinamento; al rilascio il grafico restituisce da-a alla funzionalità, che li
   scrive nell'indirizzo come `from`/`to` e li passa alle letture. Sul tocco il trascinamento orizzontale sul grafico
   non scorre la pagina (`touch-action: pan-y`).
2. Il cursore `Brush` sotto il grafico: scartato come unico modo, poco preciso su schermi stretti.

## Esito della decisione

Opzione 1, nel grafico condiviso; la funzionalità flussi gestisce etichetta e indirizzo.

Verifica: prova (scenari di R6.4.3 con trascinamento simulato, unit test del grafico e della conversione in
intervallo).

### Conseguenze

- Ogni grafico temporale condiviso può offrire la stessa selezione.
