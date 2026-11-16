# ADR riepilogo-dei-risultati-nell-api — Guadagno nel periodo, posizioni aperte e cicli falliti nell'API

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.2 (418), Task T6.4.2.1 (419)
- Collegate: R2.2.2 (stato e riepilogo dei flussi), R2.2.8 (periodo), R2.2.6 (statistiche)

## Contesto e problema

La panoramica dei flussi (`list_flow_overviews.py`) dà capitale iniziale, attuale e rendimento totale, ma non il
guadagno in un periodo, il numero di posizioni aperte né i cicli falliti; le statistiche del flusso accettano già
periodo e intervallo (`read_flow_statistics.py`).

## Fattori decisionali

- R6.4.2: guadagno totale e nel periodo (importo nella valuta di regolamento e percentuale), posizioni aperte,
  cicli falliti nel periodo, sia per l'elenco sia per la pagina del flusso.
- `.claude/rules/tech-dashboard.md`: nessuna logica di business nella dashboard; i numeri li calcola l'API.
- Decisione del proprietario (16/11/2026): importo e percentuale; la valuta è quella del conto, non dell'asset.

## Opzioni considerate

1. Un blocco `summary` nella panoramica dei flussi e nello stato del flusso, calcolato per il periodo o l'intervallo
   richiesto (`period`, `from`, `to` come le statistiche): guadagno totale e nel periodo (importo e percentuale sul
   capitale iniziale), posizioni aperte, cicli falliti; la valuta resta `currency`. Guadagno nel periodo dalla
   equity registrata ai capi dell'intervallo (stessa fonte dell'equity curve).
2. Comporlo nella dashboard da più chiamate: scartata, calcolo di business nel client e N chiamate per l'elenco.

## Esito della decisione

Opzione 1, nei casi d'uso esistenti del contesto `flows` con le porte che leggono equity, posizioni aperte e cicli.

Verifica: prova (unit test dei casi d'uso, test di integrazione su PostgreSQL, test dell'API).

### Conseguenze

- Elenco e pagina del flusso mostrano il riepilogo con una sola lettura ciascuno.
