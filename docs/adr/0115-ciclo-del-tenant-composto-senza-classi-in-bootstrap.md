# ADR 0115 — Il ciclo di ogni tenant si compone senza classi in bootstrap

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.2.1-R1.2.5, R1.3.5; Bug B0.0.3 (177)
- Collegate: ADR 0089 (`bootstrap.py` istanzia e collega, nessuna classe), ADR 0096 (ciclo composto per il tenant
  del flusso, che lasciava in `bootstrap.py` `TenantCyclePorts` e `CycleServices`), ADR 0104-0105 (grafo LangGraph),
  ADR 0109 (fabbriche del modello), ADR 0112 (pianificazione con APScheduler)

## Contesto e problema

Dopo ADR 0096 `bootstrap.py` componeva il ciclo in due tempi: `cycle_ports` riempiva il contenitore
`TenantCyclePorts` con gli adapter del tenant, `cycle_services` il contenitore `CycleServices` con ciò che ogni ciclo
condivide, e `run_cycle_for` li leggeva per costruire il grafo. Le due dataclass violano la regola «`bootstrap.py`:
nessuna classe» (CLAUDE.md, «Test di architettura») ed erano le ultime due voci di `known_violations.py`, legate al
Bug 177.

## Decisione

- `bootstrap.cycle_of` restituisce la funzione `tenant -> RunCycleUseCase`: dentro, per ogni tenant, istanzia gli
  adapter del tenant e compone passi del grafo (`CycleSteps`), guardie (`CycleGuards`) e checkpointer direttamente,
  senza contenitori intermedi. Le fabbriche del modello (`ModelGateways`) e il forecaster arrivano come argomenti;
  orologio, fonti ed exchange si istanziano una volta, fuori dalla funzione per tenant.
- `bootstrap.worker_cycles` pianifica con `PlanFlowCyclesUseCase` su APScheduler e registra il prezzo reale delle
  previsioni scadute (R1.3.5) con il repository delle previsioni di ogni tenant.
- L'harness degli scenari, che sostituisce una porta del tenant alla volta, tiene la propria composizione sugli
  adapter finti in `tests/support/cycle_composition.py` (le stesse due dataclass, fuori dal codice di produzione).
- `tests/architecture/known_violations.py`: `Rule.BOOTSTRAP_WITHOUT_CLASSES` torna vuota e la costante
  `BUG_STRICTER_RULES` sparisce; l'elenco delle violazioni note è vuoto.

## Alternative scartate

- Tenere le dataclass e spostarle in `application/flows`: sarebbero tipi di composizione, non di business, in un
  livello che non conosce gli adapter; e il caso d'uso del ciclo riceve già `CycleSteps` e `CycleGuards`.
- Lasciare le voci nell'elenco: l'elenco può solo diminuire e il Bug 177 chiede di eliminarle.

## Confronto con le decisioni scritte

- CLAUDE.md, «Regola delle dipendenze» e «Test di architettura»: `bootstrap.py` senza classi, decisioni o costanti;
  conforme, due voci tolte da `known_violations.py`.
- CLAUDE.md, «Test»: i test di composizione del worker (`tests/unit/bootstrap/test_cycle_notifications.py`)
  verificano che `cycle_of` componga un `RunCycleUseCase` per ogni tenant.

## Conseguenze

- `bootstrap.py` non dichiara più classi; nessuna violazione nota resta aperta.
- La composizione del ciclo esiste due volte, in produzione (`cycle_of`) e nell'harness dei test
  (`cycle_composition.py`): un passo nuovo del grafo si aggiunge in entrambe. Gli scenari girano sull'harness, quindi
  un passo dimenticato in `cycle_of` lo rileva solo mypy, attraverso i campi obbligatori di `CycleSteps`.
