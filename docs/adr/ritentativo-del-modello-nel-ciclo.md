# ADR ritentativo-del-modello-nel-ciclo — Errori temporanei del modello ritentati nello stesso ciclo

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 583, Task 584; R1.2.3, R1.2.4, R1.4.6 (costo delle chiamate)
- Collegate: ADR 0109 (fabbriche della chiamata al modello), ADR 0148 (LiteLLM), ADR permanenza-decisa-dall-errore-base;
  sostituisce in parte `.claude/rules/tech-openrouter.md` («Il nuovo tentativo è il ciclo successivo») e il
  `num_retries=0` senza ritentativi di `docs/architecture.md` per gli errori di disponibilità
- Verifica: prova

## Contesto e problema

`AskAgentUseCase` (`application/agent/ask_agent.py:39-71`) fa una sola chiamata al modello per ciclo; un
`ModelUnavailableError` fa fallire il ciclo e il nuovo tentativo è il ciclo successivo. Il proprietario (17/11/2026)
ha visto un ciclo fallito per un errore temporaneo di OpenRouter e ha deciso: «Riprova sempre», anche se la chiamata
potrebbe essere stata addebitata.

## Fattori decisionali

- Decisione del proprietario (17/11/2026): ritentare nello stesso ciclo ogni errore temporaneo.
- La permanenza la decide l'errore base: chiave rifiutata e credito esaurito restano permanenti e non si ritentano.
- R1.4.6: il costo di ogni chiamata partita si registra.
- R1.4.5 resta: una risposta arrivata ma non conforme non si ritenta (non è un errore di disponibilità).
- `domain` e `application` non usano librerie tecniche: l'attesa passa da una porta.

## Decisione

- Application: `AskAgentUseCase` ripete la chiamata fino a 2 volte dopo la prima (3 tentativi) quando riceve un
  `ModelUnavailableError` non permanente, con attese di 5 e 15 secondi. Un errore permanente esce subito. Dopo
  l'ultimo tentativo fallito esce l'ultimo errore.
- Costo: il costo e l'esito (chiamata partita senza costo noto) di ogni tentativo fallito si sommano a quelli della
  chiamata riuscita o dell'errore finale, così il ciclo registra il costo di tutti i tentativi.
- Nuova porta `PausePort.pause(seconds)` in `application/agent/ports.py`, realizzata da `SystemClockPauseAdapter` in
  `adapters/outbound/system_clock/`; i test usano un finto che registra le attese.
- Le regole `.claude/rules/tech-openrouter.md` e `docs/architecture.md` si allineano: errori temporanei ritentati nel
  ciclo dal caso d'uso; gli adapter continuano a non ritentare.
- Scenari: nuovo scenario in F1.4 (errore temporaneo poi risposta: decisione presa, costo dei due tentativi; errori
  temporanei tre volte: ciclo fallito; chiave rifiutata: nessun nuovo tentativo).

## Alternative scartate

- Ritentativo negli adapter (`num_retries` di LiteLLM, ciclo in OpenRouter): due politiche diverse e costo dei
  tentativi non visibile al ciclo.
- Solo quando non addebitato: scartata dal proprietario.

## Conseguenze

- Un ciclo può durare fino a tre attese del modello più 20 secondi.
