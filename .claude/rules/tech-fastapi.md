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
- **Errori**: una mappa unica da errore tipizzato a stato HTTP. `*NotFoundError` e
  `CrossTenantAccessError` diventano entrambi 404 con lo stesso corpo. Un errore non mappato è un
  difetto da correggere, non un 500 accettato.
- Ogni risposta dichiara l'ambiente dell'installazione (R0.1.4).
- La pagina OpenAPI usa il login Entra con Authorization Code + PKCE.
