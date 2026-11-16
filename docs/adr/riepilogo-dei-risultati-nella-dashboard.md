# ADR riepilogo-dei-risultati-nella-dashboard — Riepilogo dei risultati nella pagina del flusso e nell'elenco

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.2 (418), Task T6.4.2.2 (420)
- Collegate: ADR riepilogo-dei-risultati-nell-api, ADR ritocchi-delle-pagine-della-dashboard (legenda degli esiti)

## Contesto e problema

La pagina del flusso e le schede dell'elenco non dicono in cima come sta andando il flusso; le schede dell'elenco
hanno una fila di esiti dei cicli che non informa e la voce Ambiente, già indicata in alto.

## Fattori decisionali

- R6.4.2 e decisioni del proprietario (16/11/2026): importo e percentuale, colori verde/rosso, errori evidenziati solo
  se presenti, fila degli esiti tolta.

## Opzioni considerate

1. Un componente di riepilogo della funzionalità flussi, quattro valori in griglia (due colonne su telefono, quattro
   su schermo largo): guadagno totale, guadagno nel periodo, posizioni aperte (collegamento alle posizioni aperte),
   cicli falliti (collegamento ai cicli filtrati sui falliti, rosso solo se maggiore di zero). Usato in cima alla
   pagina del flusso e in ogni scheda dell'elenco; la fila degli esiti, la sua legenda e la voce Ambiente si
   tolgono; conto, modello, versione ed esecuzioni restano in secondo piano.
2. Un grafico in miniatura per scheda: scartato, più pesante e meno leggibile dei numeri.

## Esito della decisione

Opzione 1, con i dati del blocco `summary` dell'API.

Verifica: prova (scenari di R6.4.2, unit test del componente).

### Conseguenze

- Il colpo d'occhio sul flusso arriva prima di ogni dettaglio, nell'elenco e nella pagina.
