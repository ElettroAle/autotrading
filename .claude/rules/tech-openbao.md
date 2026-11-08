---
paths:
  - "src/autotrading/adapters/outbound/openbao/**"
  - "tests/unit/adapters/openbao/**"
  - "tests/integration/openbao/**"
---

# Adapter in uscita: OpenBao

- Client hvac, importato solo in questa cartella.
- Percorso KV: `tenants/<tenant_id>/accounts/<account_id>`. L'adapter è legato al tenant e costruisce
  il percorso da solo; non accetta percorsi dall'esterno.
- Autenticazione del servizio con AppRole; il `secret_id` si legge da file montato in sola lettura.
  **Mai variabili d'ambiente.**
- Token a vita breve, rinnovato dall'adapter.
- I permessi di ciascuna identità sono in `docs/architecture.md` §8.2: l'adapter non li allarga e
  non li aggira.
- Le eccezioni hvac si traducono negli errori del contratto di `SecretVaultPort`.
- Il contenuto dei segreti non compare in log, errori o repr.
