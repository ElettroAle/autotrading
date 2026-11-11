---
paths:
  - "src/autotrading/adapters/inbound/api/**"
  - "tests/unit/adapters/api/**"
  - "tests/integration/api/**"
---

# Adapter in ingresso: FastAPI ed Entra ID

- Il router traduce: richiesta ──> comando ──> `UseCase.execute` ──> risposta. Nessuna logica di business.
- Gli schemi pydantic di richiesta e risposta stanno solo qui; mai passati al livello application.
- **Autenticazione**: token Entra validato con le chiavi JWKS dell'issuer, controllo di issuer,
  audience e ruolo `Utente`. Senza ruolo: 403 e nessun tenant creato (R0.1.1). L'`oid` è l'unico
  identificativo dell'utente.
- Il tenant si risolve con `ResolveTenantUseCase`, poi `bootstrap.for_tenant` fornisce i casi d'uso.
- **Errori** (ADR 0027): `install_error_responses` installa l'unico handler centrale di ogni servizio
  (API e `worker`). Ogni risposta d'errore è Problem Details (`application/problem+json`) con `type`,
  `title`, `status`, `detail`, i `details` dell'errore, `requestId` e `traceId` (dal `traceparent` W3C
  se valido). Lo stato è quello che l'errore tipizzato dichiara; `NotImplementedError` risponde 501;
  ogni altra eccezione 500 con un `detail` generico, registrata nel log con `requestId` e `traceId`.
  Una richiesta non valida risponde 422 con `errors` (dove e perché), mai con l'input.
  `*NotFoundError` e `CrossTenantAccessError` rispondono entrambi 404 con lo stesso `detail`.
- Ogni risposta dichiara l'ambiente dell'installazione (R0.1.4).
- La pagina OpenAPI usa il login Entra con Authorization Code + PKCE.
