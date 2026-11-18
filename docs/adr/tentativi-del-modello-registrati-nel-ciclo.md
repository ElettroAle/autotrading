# ADR tentativi-del-modello-registrati-nel-ciclo — Tre nuovi tentativi del modello con attese 2, 8 e 30 secondi, registrati nel ciclo

- Stato: proposta (18 novembre 2026)
- Requisiti: US 530 R1.4.9, Task 531 e 532; R1.2.3, R1.4.6
- Collegate: sostituisce in parte ADR ritentativo-del-modello-nel-ciclo (numero dei tentativi e attese); ADR
  permanenza-decisa-dall-errore-base; ADR 0099 (registro del ciclo); `.claude/rules/tech-openrouter.md`,
  `.claude/rules/tech-litellm.md`, `.claude/rules/context-agent.md`
- Verifica: prova

## Contesto e problema

Con il Bug 583 `AskAgentUseCase` (`application/agent/ask_agent.py`) ritenta un `ModelUnavailableError` non permanente
fino a 2 volte, con attese di 5 e 15 secondi (`RETRY_PAUSES_SECONDS`), e somma il costo di ogni tentativo. R1.4.9,
scritta dal proprietario, chiede fino a 3 nuovi tentativi con attese di 2, 8 e 30 secondi e il numero dei tentativi
registrato nel ciclo. I numeri di oggi sono una scelta dell'ADR ritentativo-del-modello-nel-ciclo, ancora in proposta,
non del proprietario.

## Fattori decisionali

- R1.4.9 (proprietario): 3 nuovi tentativi, attese 2, 8 e 30 secondi; il ritentativo sta nel caso d'uso, non
  nell'adapter; permanenti mai ritentati; costo di ogni tentativo e numero dei tentativi registrati nel ciclo.
- La permanenza la decide l'errore base (CLAUDE.md): nessuna classificazione nuova.
- R1.4.5 resta: una risposta letta ma non conforme non si ritenta.
- `domain` e `application` senza librerie tecniche: l'attesa resta `PausePort`.

## Decisione

- `RETRY_PAUSES_SECONDS = (2.0, 8.0, 30.0)`: fino a 4 chiamate per ciclo; il ciclo di `_reply_of` resta lo stesso.
- `ModelSpend` conta le chiamate partite o tentate della domanda (`attempts`, 1 per la prima); `AgentAnswer` e
  `ModelUnavailableError.with_spend` portano il numero dei tentativi insieme al costo.
- Il registro del ciclo (`JsonCycleJournalAdapter`) scrive i tentativi accanto al costo della chiamata, sia per una
  decisione presa sia per un passo dell'agente fallito; le letture del ciclo che espongono il costo della chiamata
  espongono anche i tentativi.
- Testi allineati nello stesso lavoro (Task 532): R1.2.3 e R1.4.6 (2, 8 e 30 secondi, fino a 3 nuovi tentativi; gli
  scenari di R1.4.6 con le attese nuove), `tech-openrouter.md`, `tech-litellm.md`, il commento e la docstring del
  caso d'uso. Nuovo `.feature` R1.4.9.

## Alternative scartate

- Lasciare 5 e 15 secondi: contraddice R1.4.9.
- Ritentativo negli adapter: escluso da R1.4.9 e dall'ADR ritentativo-del-modello-nel-ciclo.

## Conseguenze

- Un ciclo può durare fino a 40 secondi di attese più quattro chiamate al modello.
