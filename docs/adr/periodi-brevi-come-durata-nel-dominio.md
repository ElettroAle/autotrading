# ADR periodi-brevi-come-durata-nel-dominio — Periodi brevi come durata fino a ora nel dominio e nell'API

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.6 (Task 538)
- Collegate: ADR periodo-al-minuto (che questa estende ai periodi brevi), ADR 0122 (statistiche del flusso per
  periodo), ADR 0136 (classifica con il periodo), R2.2.6, R2.4.2, R6.4.3

## Contesto e problema

`StatisticsPeriodKind` ha `all`, `7d`, `30d` e `range`. La finestra dei periodi «ultimi N» si calcola da
`LAST_DAYS` in giorni. R6.4.6 aggiunge 30 minuti, 1 ora, 12 ore e 24 ore, validi fino a ora e al minuto, per
tutto ciò che il periodo filtra:
- riepilogo, equity e statistiche;
- classifica, storico e accuratezza della previsione;
- panoramica dei flussi.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): periodi «dal più breve, default tutta la vita».
- ADR periodo-al-minuto: finestre al minuto, `TimeWindow.of_minutes`; i periodi «ultimi N» valgono da adesso.
- CLAUDE.md: le regole sui valori stanno nel domain; un solo `StatisticsPeriod.named` per tutte le letture (oggi in
  `history.py`, `list_flow_overviews.py`, `rank_flows.py`, `read_flow_equity.py`, `read_flow_results.py`,
  `read_flow_statistics.py`, `read_forecast_accuracy.py`).
- R6.4.6, scenario «Periodo sconosciuto»: 400 con l'elenco dei periodi validi, già dato da
  `UnknownStatisticsPeriodError`.

## Opzioni considerate

1. **Durata per ogni periodo «ultimi N».**
   - `StatisticsPeriodKind` riceve `LAST_30_MINUTES = "30m"`, `LAST_HOUR = "1h"`, `LAST_12_HOURS = "12h"` e
     `LAST_24_HOURS = "24h"`, in ordine dal più breve.
   - `LAST_DAYS` diventa `LAST_DURATIONS: dict[StatisticsPeriodKind, timedelta]` per i sei periodi «ultimi N».
   - `window(now)` restituisce la finestra da `now - durata` a ora, tagliata al minuto con `TimeWindow.of_minutes`
     come l'intervallo. Così «1 ora» alle 10:15 vale dalle 9:15 comprese, come nello scenario «Ultima ora».
   - Ogni lettura che passa da `StatisticsPeriod.named` riceve i periodi senza modifiche proprie. Le rotte che
     validano `period` a parte (enum FastAPI, se ce ne sono) leggono lo stesso enum.
2. **Periodo libero in minuti (`period=90m`)**: scartata, perché il proprietario ha scelto un menu con valori fissi.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test di `StatisticsPeriod` per ogni durata, con taglio al minuto e periodo sconosciuto con l'elenco.
- Test di una rotta per lettura.
- Scenari di R6.4.6 sui casi d'uso, compresa la classifica sulle ultime 24 ore.

### Conseguenze

- `7d` e `30d` diventano finestre al minuto da adesso, come già dice ADR periodo-al-minuto.
