# ADR errore-di-openrouter-nella-risposta — L'errore che OpenRouter mette nel corpo di una risposta 200 diventa il motivo

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 583, Task 585; R1.2.3
- Collegate: ADR 0109, `.claude/rules/tech-openrouter.md`, ADR permanenza-decisa-dall-errore-base
- Verifica: prova

## Contesto e problema

Quando il fornitore dietro OpenRouter fallisce, OpenRouter può rispondere 200 con `{"error": {"code", "message"}}`.
`OpenRouterModelCallAdapter._usage_of` cade su `document["usage"]` e l'adapter solleva «risposta del fornitore
inattesa» (`adapters/outbound/openrouter/model_call.py:62-65`): il motivo vero si perde.

## Fattori decisionali

- Bug 583: il motivo mostrato è l'errore vero del fornitore.
- La chiave non va mai in un errore o in un log; il messaggio del fornitore si limita come oggi (`ORIGINAL_LIMIT`).
- La permanenza la decide l'errore base dal codice conservato.

## Decisione

- Prima di leggere `usage`, se il documento ha `error` con `message`, l'adapter lo tratta come un rifiuto: con un
  `code` numerico passa dalla stessa traduzione dei codici HTTP di `_refusal` (401/403 chiave rifiutata, 402 credito
  esaurito, altri temporanei), altrimenti `ModelUnavailableError(OPENROUTER, <messaggio>, sent=True)`; il costo, se
  `usage` c'è, resta.
- Prove: unit test con risposta 200 ed errore con e senza codice; il motivo contiene il messaggio di OpenRouter.

## Alternative scartate

- Motivo generico con il corpo nei log: l'utente non vedrebbe la causa.

## Conseguenze

- Notifica e storico del ciclo dicono perché il fornitore ha fallito.
