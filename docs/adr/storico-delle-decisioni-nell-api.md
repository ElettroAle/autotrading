# ADR storico-delle-decisioni-nell-api — Storico delle decisioni per ciclo e asset nell'API

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.5 (Task 525)
- Collegate: ADR decisioni-del-ciclo-registrate-per-asset (R6.5.4, tabella `cycle_decisions`), ADR
  filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api, ADR periodo-al-minuto, R6.4.3, R6.4.4

## Contesto e problema

R6.5.5 vuole l'elenco delle decisioni del flusso, una riga per ciclo e asset, dalle più recenti. Deve seguire il
periodo comune della pagina, filtrarsi per asset, azione e direzione e paginarsi come le altre tabelle.

## Fattori decisionali

- Memoria «no provisional duplicates»: si legge la tabella `cycle_decisions` di R6.5.4, nessuna seconda lettura dei
  documenti.
- ADR filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api: filtri e pagina come per i cicli (`CycleFilter`,
  `CyclePage`) e periodo con `IntervalStart`/`IntervalEnd`.
- ADR periodo-al-minuto: il periodo arriva come `StatisticsPeriod` (`period`, `from`, `to`) al minuto.
- CLAUDE.md: un caso d'uso per modulo, porte nel `ports.py` del contesto, multi-tenancy con RLS nell'adapter.

## Opzioni considerate

1. **`ListDecisionsUseCase` sopra `DecisionHistoryPort`.**
   - Domain `flows`: `DecisionFilter(asset | None, action | None, direction | None)` e `DecisionPage(number,
     decisions, has_next, total)`. Ogni voce è un `RecordedDecision` con `planned_at`.
   - `ListDecisionsUseCase` (`application/flows/list_decisions.py`) legge il flusso del tenant (404), compone la
     finestra dal periodo e chiede una pagina alla porta.
   - Dei cicli si leggono solo quelli conclusi (R6.5.5, «cicli conclusi»), come per l'ultima decisione di R6.5.4.
   - `SqlAlchemyCycleRepositoryAdapter` realizza la porta sulla tabella `cycle_decisions`, unita a `cycles` per
     l'esito. Ordine `planned_at` decrescente, poi asset. La dimensione della pagina è quella dei cicli.
   - Rotta `GET /flows/{flow_id}/decisions` con `period`, `from`, `to`, `asset`, `action`, `direction` e `page`.
     Valori sconosciuti danno 400 in Problem Details.
2. **Filtro nel browser su tutte le decisioni**: scartata, perché in 30 giorni con un ciclo ogni 15 minuti sono
   migliaia di righe, e la paginazione sta già nell'API per i cicli.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test del filtro, della pagina e del caso d'uso.
- Test d'integrazione dell'adapter con RLS.
- Test della rotta.
- Scenari di R6.5.5 sui casi d'uso con adapter finti.

### Conseguenze

- Parte dopo l'integrazione di R6.5.4 (tabella) e di R6.5.3 (icone).
