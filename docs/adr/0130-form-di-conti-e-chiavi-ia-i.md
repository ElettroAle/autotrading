# ADR 0130 — Form di conti e chiavi IA: i segreti si scrivono e non si rileggono

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.3.1 (Task T2.3.1.1), R2.3.2 (Task T2.3.2.1)
- Collegate: ADR 0116 (React Hook Form + Zod), ADR 0119, ADR 0007 (credenziali leggibili solo dal worker),
  ADR 0027 (Problem Details); API `/accounts`, `/provider-keys`

## Contesto e problema

Registrazione e sostituzione di credenziali dei conti e chiavi dei fornitori IA passano dal browser. I segreti non
devono restare nella pagina né tornare indietro dall'API.

## Decisione

- Funzionalità `accounts` e `provider-keys`, form con React Hook Form + Zod; campi segreti `type="password"`,
  `autocomplete="off"`, svuotati dopo l'invio, mai in cache TanStack né nei log.
- La validazione nel browser controlla solo forma e presenza; le regole restano all'API, e i Problem Details di
  ritorno si mostrano accanto al campo indicato o in testa al form.
- Rimozione di un conto in due passi, come prevede l'API (R0.2.5, R1.1.8): `DELETE /accounts/{id}` senza conferma;
  se l'API risponde 409 (flussi attivi o in pausa, posizioni aperte), la finestra di conferma mostra il motivo del
  Problem Details, che nomina i flussi e ciò che accadrà; la conferma ripete la richiesta con `confirmed=true`.
  Rimozione di una chiave con una finestra di conferma che nomina il fornitore.
- L'elenco delle chiavi mostra fornitore e data di registrazione: `GET /provider-keys` (e le risposte di
  registrazione e sostituzione) aggiungono `registered_at`, l'istante dell'ultima registrazione o sostituzione già
  salvato dall'adapter SQL (`updated_at`), letto dalla porta del contesto `agent` estesa a restituirlo.

## Alternative scartate

- **Validazione completa replicata nel browser**: risposte più rapide, ma regole duplicate che divergono.

## Conseguenze

- Un modulo condiviso in `src/lib` traduce i Problem Details negli errori dei campi, riusato dagli altri form di E2.
