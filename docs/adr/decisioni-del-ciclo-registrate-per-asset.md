# ADR decisioni-del-ciclo-registrate-per-asset — Decisioni del ciclo registrate per asset e ultima decisione nell'API

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.4 (Task 522); la stessa registrazione serve a R6.5.5 (Task 525)
- Collegate: ADR 0099 (contesto, decisioni e registro del ciclo in flows), ADR 0104, ADR 0120 (equity registrata a
  ogni ciclo, precedente di un dato del ciclo in una tabella propria), R1.4.4, R3.1.4, `.claude/rules/context-flows.md`,
  `.claude/rules/tech-sqlalchemy.md`

## Contesto e problema

Le decisioni dell'agente oggi stanno solo nel documento JSON del passo `agent_decision` (`cycles.documents`, scritto
da `JsonCycleJournalAdapter` con le chiavi `risposta`, `decisioni`, `scartate`, `mancanti`). R6.5.4 vuole l'ultima
decisione per asset con azione, direzione, confidenza e ragionamento. R6.5.5 vuole lo storico filtrabile per asset,
azione e direzione, con paginazione. Filtrare e paginare dentro un JSON per ciclo non si fa in SQL e lega l'API alla
forma del documento.

## Fattori decisionali

- CLAUDE.md: `domain` senza librerie; il caso d'uso orchestra; il grafo (`cycle_graph.py`) è generico sui tipi
  dell'agente e legge ciò che gli serve attraverso il registro (`CycleJournalPort`), come già fa per
  `call_cost(decision)`.
- Memoria «no provisional duplicates»: una sola lettura delle decisioni, che R6.5.5 riusa.
- R3.1.4: la confidenza è un intero da 0 a 100. Le decisioni registrate prima di R3.1.4 non ce l'hanno.
- R6.5.4: «ultimo ciclo concluso con una decisione». Un ciclo fallito prima della decisione non la sostituisce.

## Opzioni considerate

1. **Tabella `cycle_decisions` scritta con il ciclo.**
   - Domain `flows`: `RecordedDecision(asset, action, direction | None, confidence | None, reasoning)`.
     - `action` è uno dei quattro valori di `TradeAction`, come testo del domain `flows`.
     - `direction` è presente solo per un'apertura.
   - `CycleRecord` riceve `decisions: tuple[RecordedDecision, ...]`.
   - Il registro del ciclo riceve `recorded_decisions(decision) -> tuple[RecordedDecision, ...]` accanto a
     `call_cost`. Il nodo `_decide` lo mette nello stato e `_record_of` nel record, quindi anche un ciclo fallito dopo
     la decisione conserva le sue decisioni.
   - `SqlAlchemyCycleRepositoryAdapter` scrive le righe nella stessa transazione del ciclo: `tenant_id`, `flow_id`,
     `planned_at`, `asset`, `action`, `direction`, `confidence`, `reasoning`. Ha RLS per tenant come le altre tabelle,
     indice su `(flow_id, planned_at)` e chiave esterna verso `cycles`.
   - La migrazione riempie la tabella dai documenti esistenti (`documents` → passo `agent_decision` → `decisioni`).
     Una decisione senza confidenza ha `confidence` nullo.
   - `ReadLastDecisionUseCase`, in `application/flows/read_last_decision.py`, restituisce l'istante e le decisioni
     dell'ultimo ciclo **concluso** del flusso del tenant che ne ha, oppure nessuna.
   - Rotta `GET /flows/{flow_id}/decisions/latest`: 200 con `planned_at` e le decisioni, oppure 200 con `null`.
2. **Leggere l'ultimo documento JSON a ogni richiesta**: scartata. Andrebbe bene per R6.5.4, ma non per i filtri di
   R6.5.5, e due letture diverse delle stesse decisioni sono il doppione da evitare.
3. **Colonna JSONB con indici GIN**: scartata, perché la paginazione e i filtri per azione e direzione restano
   legati alla forma del documento.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test di `RecordedDecision`, del registro (`recorded_decisions`), del nodo del grafo e di
  `ReadLastDecisionUseCase`: ultimo concluso; ciclo fallito ignorato; nessun ciclo.
- Test d'integrazione dell'adapter e della migrazione con il riempimento.
- Scenari di R6.5.4.

### Conseguenze

- R6.5.5 legge la stessa tabella: parte dopo l'integrazione di R6.5.4 e di R6.5.3.
- Nello stesso lavoro il filtro dei cicli per decisione (R6.4.4) passa dal contenimento JSON su `documents` alla
  tabella `cycle_decisions`, con un `EXISTS`. Le chiavi `DECISIONS` e `RECORDED_ACTIONS` di `cycle_repository.py`
  restano solo per il riempimento della migrazione, per evitare due letture delle decisioni.
- La confidenza delle decisioni registrate prima di R3.1.4 risulta «non disponibile».
