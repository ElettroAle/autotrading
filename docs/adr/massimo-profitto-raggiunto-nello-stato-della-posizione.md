# ADR massimo-profitto-raggiunto-nello-stato-della-posizione — Massimo profitto non realizzato raggiunto nello stato della posizione

- Stato: accettata (26 novembre 2026)
- Requisiti: US 749 R5.5.1 (Task 751)
- Collegate: ADR sorveglianza-del-prezzo-per-lo-stop-che-segue, ADR stop-e-obiettivo-in-vigore-nello-stato-della-posizione;
  `.claude/rules/context-flows.md`, `.claude/rules/context-agent.md`
- Verifica: prova

## Contesto e problema

R5.5.1 chiede il massimo profitto non realizzato raggiunto da una posizione aperta, nella valuta del conto, in API, MCP
e dashboard solo per i flussi con distanza o pareggio; all'agente solo con l'opzione accesa; vuoto per gli altri flussi.

## Fattori decisionali

- Solo le posizioni sorvegliate hanno il dato: lo tiene la sorveglianza del prezzo (ADR
  sorveglianza-del-prezzo-per-lo-stop-che-segue).
- Una sola lettura dello stato per agente, API, MCP e dashboard (`ReadFlowStateUseCase`).

## Decisione

- Il massimo profitto raggiunto è (miglior prezzo − prezzo d'ingresso) × dimensione per un long, il contrario per uno
  short, mai sotto zero; lo calcola il domain e lo registra la sorveglianza con il miglior prezzo.
- `ReadFlowStateUseCase` lo aggiunge alla posizione solo se la configurazione ha distanza o pareggio; altrimenti è
  vuoto. API e strumenti MCP lo espongono così.
- Il contesto dell'agente lo riporta solo con l'opzione accesa; con l'opzione spenta la riga non c'è, e il resto dello
  stato è identico a oggi.

## Alternative scartate

- **Calcolarlo dalle equity registrate dei cicli**: non vede i prezzi tra i cicli.

## Conseguenze

- Il dato esiste solo dalla prima sorveglianza della posizione.
