# ADR 0122 — Le statistiche del flusso per periodo si calcolano nel dominio dalle posizioni chiuse e dal costo

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.6 (Task T2.2.6.1); base di R2.4.2
- Collegate: RF-23.05; R1.6.2 (posizioni chiuse, `ListClosedPositionsUseCase`); R1.4.x (costo del modello,
  `ReadFlowCostUseCase`); ADR 0018 (numeri come stringhe nell'API); ADR 0027 (errori in Problem Details)

## Contesto e problema

La dashboard mostra per un periodo vinte, perse, win rate, PnL medio di vincenti e perdenti, commissioni,
numero di operazioni e costo del modello. La regola di calcolo (pareggio né vinto né perso, win rate su vinte più
perse, win rate non disponibile senza operazioni decisive) è di business e la usa anche la classifica (R2.4.2):
non può stare nel frontend.

## Decisione

- Value object `FlowStatistics` nel dominio `flows`, costruito da una sequenza di posizioni chiuse e dal costo del
  modello: la regola del pareggio e del win rate vive solo qui. Il win rate è `None` quando vinte più perse è zero.
- Value object `StatisticsPeriod` nel dominio (tutta la vita, ultimi 7 giorni, ultimi 30 giorni, intervallo
  `da`-`a` con `da` non successivo ad `a`), riusato da equity curve e classifica dove serve un periodo.
- Caso d'uso `ReadFlowStatisticsUseCase` del contesto `flows`: legge le posizioni chiuse del flusso nel periodo e
  il costo delle chiamate al modello nel periodo dalle porte esistenti del contesto (estese con il filtro per
  periodo se oggi non lo hanno), poi costruisce `FlowStatistics`.
- API: `GET /flows/{flow_id}/statistics?period=all|7d|30d|range&from=&to=`; importi come stringhe (ADR 0018),
  win rate come stringa percentuale con due decimali o `null`; periodo non valido = errore del dominio, 400.

## Alternative scartate

- **Calcolo nel frontend dalle posizioni chiuse paginate**: nessun endpoint nuovo, ma la regola si duplicherebbe
  nella classifica e richiederebbe di scaricare tutte le pagine.
- **Vista SQL aggregata**: veloce, ma sposta la regola del pareggio nell'adapter.

## Conseguenze

- La classifica (R2.4.2) riusa `FlowStatistics` e `StatisticsPeriod` senza ricalcolare a modo suo.
