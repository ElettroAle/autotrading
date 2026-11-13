# ADR 0099 — Contesto, decisioni, rischio e registro del ciclo nel contesto flows

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.4.3-R1.4.6, R1.5.1-R1.5.4, R1.7.1; Bug 170, Bug B0.0.3 (177)
- Supera: ADR 0042 nelle parti in cui contesto dell'agente, decisione, controllo del rischio e descrizione del
  registro del ciclo vivono in `bootstrap.py` (`ContextFromAgent`, `AgentFromAgent`, `RiskFromFlows`,
  `CycleJournalFromContexts`, `CycleContext`, `CycleDecisions`)
- Collegate: ADR 0088 (porte del consumatore), ADR 0089 (niente ponti), ADR 0094 (ciclo nel contesto flows),
  ADR 0098 (ordini del ciclo)

## Contesto e problema

Quattro passi del ciclo erano classi di `bootstrap.py`: componevano il contesto dell'agente, chiamavano il modello,
traducevano le decisioni per il controllo del rischio e descrivevano ogni passo per il registro. `bootstrap.py`
prendeva decisioni e importava i tipi di `agent` dentro il ciclo di `flows`.

## Decisione

- `flows` dichiara la domanda del ciclo come tipo del proprio dominio: `CycleQuestion`, con `FlowStateView`,
  `PositionView` e `SourceData` (gli stessi nomi e campi di prima, così il documento del registro non cambia).
  `CycleFlow.state_view()` sostituisce `_state_view` di `bootstrap.py`.
- `flows` dichiara in `ports.py` le porte del consumatore verso `agent` (`AgentPromptComposerPort`,
  `FlowAgentPort`, con le forme lette `AgentReplyPort`, `AgentResponsePort`, `AgentDecisionPort`, ...) e i tipi
  `CycleContext` e `CycleDecisions`.
- Casi d'uso di `flows`: `ComposeCycleContextUseCase`, `DecideCycleUseCase`, `ReviewCycleRiskUseCase`.
  `CheckRiskUseCase` riceve i limiti per exchange e sceglie quelli dell'exchange del conto del flusso; un exchange
  senza limiti è `FlowExchangeUnavailableError`.
- `agent` dichiara la forma con cui riceve la domanda (`AgentQuestionPort` e le porte dello stato e delle fonti) e
  i casi d'uso `ComposeAgentContextUseCase` e `AskFlowAgentUseCase`, che li soddisfano strutturalmente.
- Il registro del ciclo è `JsonCycleJournalAdapter` in `adapters/outbound/json`, adapter di `CycleJournalPort` che
  usa `json_document`: una sola tecnologia, nessuna porta ricevuta.
- I metodi delle porte dei passi si chiamano `execute`, così i casi d'uso le soddisfano senza adattatori.

## Confronto con le decisioni scritte

- CLAUDE.md, «Regola delle dipendenze»: `flows` e `agent` non si importano; si incontrano per struttura in
  `bootstrap.py`, che solo collega; conforme.
- CLAUDE.md, «Principi di codice» e `.claude/rules/layer-adapters.md` (un adapter, una tecnologia): conforme; tolte
  da `known_violations.py` le ultime voci del Bug 170 e sei del Bug 177.
- `docs/architecture.md` §5 (ciclo come grafo LangGraph): non toccato, lavoro successivo.

## Conseguenze

- Il Bug 170 non ha più voci: il ciclo sta in `flows` con le sue porte verso `agent`, `sources` e `orders`.
- Restano per il Bug 177 `SourcesFromSources`, `TenantCyclePorts`, `CycleServices` e `RunCycleUseCase` generico.
