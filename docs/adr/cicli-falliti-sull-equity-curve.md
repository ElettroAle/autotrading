# ADR cicli-falliti-sull-equity-curve — Cicli falliti come segni sull'equity curve

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.3 (421), Task T6.4.3.3 (424)
- Collegate: ADR 0121 (grafici con Recharts), ADR filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api

## Contesto e problema

Gli errori dei cicli oggi si vedono come fila di esiti nell'elenco e come righe nella pagina; il proprietario vuole
vederli sul grafico solo quando ci sono, con un simbolo preciso (16/11/2026).

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile (schede `ViewTabs`, tabella condivisa, riepilogo, grafici di `src/components/charts`), nessun duplicato per pagina.
- R6.4.3: segno rosso riconoscibile solo per i cicli falliti, che porta al dettaglio del ciclo.
- ADR 0121: i grafici condivisi ricevono i dati dalla funzionalità.

## Opzioni considerate

1. Il grafico condiviso accetta una serie di eventi (istante, etichetta, destinazione) disegnati come segni ✗ rossi
   sull'asse dell'equity; la funzionalità flussi li legge dai cicli filtrati sui falliti nell'intervallo
   (`outcome=fallito`) e passa la destinazione del dettaglio del ciclo. Il segno ha un nome accessibile.
2. Colorare di rosso i punti dell'equity: scartato, confonde perdita ed errore.

## Esito della decisione

Opzione 1.

Verifica: prova (scenario di R6.4.3, unit test del grafico con eventi).

### Conseguenze

- Errori e andamento si leggono insieme; lo stesso meccanismo può mostrare altri eventi in futuro.
