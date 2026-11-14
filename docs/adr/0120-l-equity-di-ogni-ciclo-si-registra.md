# ADR 0120 — L'equity di ogni ciclo si registra nella tabella `equity_snapshots`

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.3 (Task T2.2.3.1); base di R2.4.2 e R2.4.3
- Collegate: docs/architecture.md §3 (tabella `equity_snapshots`, «istantanea per flusso a ogni ciclo», serie
  temporale partizionata per mese) e §6 («`equity_snapshots` a ogni ciclo»); R1.6.1 (stato attribuito del flusso);
  ADR 0104-0105 (grafo del ciclo); ADR 0115

## Contesto e problema

L'equity curve chiede un punto per ciclo: capitale allocato più PnL realizzato e non realizzato, meno le
commissioni, anche per un ciclo fallito dopo la lettura dello stato. In E1 lo stato del flusso finisce solo nel
documento del ciclo, che non si interroga per periodo in modo efficiente.

## Decisione

- Tabella `equity_snapshots` come prevede `docs/architecture.md` §3: tenant, flusso, istante pianificato del ciclo,
  equity, capitale allocato, PnL realizzato, PnL non realizzato, commissioni; chiave (flusso, istante); RLS per
  tenant; partizionata per mese come le altre serie temporali.
- Il valore è un value object del dominio `flows` calcolato dallo stato attribuito (R1.6.1). Lo registra il caso
  d'uso che chiude il ciclo, anche quando il ciclo fallisce dopo `load_state`, tramite una porta del contesto
  `flows` realizzata in `adapters/outbound/sqlalchemy/`.
- Lettura per periodo (tutta la vita, 7 giorni, 30 giorni, intervallo) con un caso d'uso ed endpoint
  `GET /flows/{flow_id}/equity` dell'API.
- I cicli precedenti non si ricostruiscono (fuori ambito del requisito).

## Alternative scartate

- **Equity letta dai documenti dei cicli**: nessuna tabella nuova, ma contraddice la tabella prevista
  dall'architettura e costa una scansione dei documenti a ogni curva.
- **Un punto al giorno**: scartato dal proprietario nell'intervista.

## Conseguenze

- Il drawdown della classifica (R2.4.2) e le curve sovrapposte (R2.4.3) leggono questa tabella.
