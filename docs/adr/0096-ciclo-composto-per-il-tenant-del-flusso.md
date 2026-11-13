# ADR 0096 — Il ciclo si compone per il tenant del suo flusso

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.2.1-R1.2.5, R1.3.5, R1.8.2, R0.1.3; Bug 170, Bug B0.0.3 (177)
- Supera: ADR 0042 nella parte del `FlowDirectory` che ritrova il tenant di ogni flusso pianificato
  (`CyclesOfTenants`, porte del ciclo cercate per flusso); ADR 0092 nella parte di `TellCycleFailureUseCase`;
  rende superflua la proposta di ADR 0093 (PR #95), che teneva il tenant nel caso d'uso del ciclo
- Collegate: ADR 0094 (ciclo nel contesto flows), ADR 0089 (niente ponti), CLAUDE.md (Flusso di una richiesta)

## Contesto e problema

Il caso d'uso del ciclo era uno solo per tutto il worker e nominava solo il flusso: per eseguire un passo,
`bootstrap.py` ritrovava il tenant del flusso in una directory in memoria e costruiva le porte di quel tenant.
Ne nascevano classi di instradamento in `bootstrap.py` (`ScheduledFlowsFromFlows`, `CyclesOfTenants`,
`FlowPauseFromFlows`, `CycleRuntime`) e un caso d'uso (`TellCycleFailureUseCase`) che esisteva solo per scegliere il
tenant. Il pianificatore conosce già il tenant di ogni flusso attivo (`TenantScheduledFlow`).

## Decisione

- `RunDueCyclesUseCase` riceve i flussi attivi con il loro tenant e una funzione `tenant -> RunCycleUseCase`:
  ogni ciclo si esegue su un caso d'uso composto con le porte del tenant del suo flusso, come una richiesta API
  passa da `bootstrap.for_tenant(tenant_id)`.
- `bootstrap.run_cycle_for` è la composizione per tenant: repository dei cicli, pausa dei flussi coinvolti
  (`PauseAffectedFlowsUseCase`) e notifica del ciclo fallito (`NotifyCycleFailureUseCase`) sono quelli del tenant.
- L'ancora della pianificazione arriva alla porta dello stato del flusso dal comando del ciclo, non da una
  directory.
- `ThreadsPlannedFlowsAdapter` ricorda solo i tenant pianificati, per i prezzi reali delle loro previsioni
  (R1.3.5): un tenant non si dimentica, come prima.

## Confronto con le decisioni scritte

- CLAUDE.md, «Flusso di una richiesta» (righe 49-60): il ciclo segue lo stesso schema, tenant noto prima della
  composizione; conforme.
- CLAUDE.md, «Principi di codice» e `.claude/rules/layer-adapters.md`: `bootstrap.py` perde quattro classi e non
  sceglie più tenant per flusso; conforme, quattro voci tolte da `known_violations.py`.
- `docs/architecture.md` §5 (ciclo come grafo LangGraph): non toccato; il passaggio a LangGraph è un lavoro
  successivo.

## Conseguenze

- Un ciclo che mette in pausa il proprio flusso registra e notifica nel tenant giusto senza rileggere il
  database: il tenant viaggia con il caso d'uso.
- Restano in `bootstrap.py` i ponti dei passi (`FlowStateFromFlows`, `SourcesFromSources`, `AgentFromAgent`,
  `OrdersFromOrders`, ...) e i contenitori `TenantCyclePorts` e `CycleServices`: escono nei passi successivi del
  Bug 170.
