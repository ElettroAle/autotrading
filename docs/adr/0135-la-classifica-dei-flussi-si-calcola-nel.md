# ADR 0135 — La classifica dei flussi si calcola nel dominio da equity per ciclo e statistiche

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.4.2 (Task T2.4.2.1)
- Collegate: ADR 0120 (equity per ciclo in `equity_snapshots`), ADR 0122 (`FlowStatistics`, `StatisticsPeriod`),
  ADR 0124 (bozze escluse), ADR 0018 (numeri come stringhe); RF-01.06, RF-03.06

## Contesto e problema

La classifica confronta i flussi non archiviati con almeno un ciclo nel periodo su rendimento, PnL, commissioni,
win rate, operazioni, drawdown massimo e costo del modello. Rendimento e drawdown si calcolano sull'equity per
ciclo del periodo; il resto segue le statistiche di R2.2.6.

## Decisione

- Value object `FlowRanking` nel dominio `flows`: rendimento del periodo (ultimo punto su primo punto) e drawdown
  massimo (la più grande discesa percentuale da un massimo precedente nel periodo) dalla serie di equity, più le
  `FlowStatistics` dello stesso periodo. Le regole vivono solo qui.
- Caso d'uso `RankFlowsUseCase` del contesto `flows`: per ogni flusso non archiviato e non in bozza legge la serie
  di equity del periodo (porta di ADR 0120) e le statistiche (caso d'uso o porte di ADR 0122); esclude i flussi
  senza punti nel periodo; ordina per rendimento decrescente.
- API: `GET /flows/ranking?period=all|7d|30d|range&from=&to=`, una riga per flusso, numeri come stringhe.
- L'ordinamento per le altre colonne lo fa la dashboard sulle righe ricevute, senza ricalcolare valori.

## Alternative scartate

- **Classifica calcolata nel frontend dalle API di equity e statistiche**: nessun endpoint, ma 2N chiamate e regole
  del drawdown nel browser.
- **Ordinamento lato API per ogni colonna**: utile con molti flussi; un utente ne ha pochi.

## Conseguenze

- Le curve sovrapposte (R2.4.3) partono dai flussi di questa classifica.
