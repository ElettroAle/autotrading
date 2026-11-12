---
paths:
  - "src/autotrading/adapters/outbound/sqlalchemy/**"
  - "migrations/**"
  - "tests/unit/adapters/sqlalchemy/**"
  - "tests/integration/sqlalchemy/**"
---

# Adapter in uscita: SQLAlchemy, Alembic, PostgreSQL

- SQLAlchemy 2 e Alembic importati solo qui e nelle migrazioni.
- Il mapping tra tabelle e oggetti di dominio sta in questa cartella; il domain non conosce l'ORM.
- Ogni modifica di schema passa da una migrazione Alembic versionata.

## Row level security

- Ogni tabella di dati posseduti ha `tenant_id` non nullo e una policy RLS
  `USING (tenant_id = current_setting('app.tenant_id')::uuid)` con `WITH CHECK` uguale.
- Le tabelle hanno `FORCE ROW LEVEL SECURITY`; il ruolo applicativo non è proprietario delle tabelle.
- La policy nasce nella stessa migrazione che crea la tabella.
- L'adapter legato al tenant imposta `set_config('app.tenant_id', <tenant>, true)` all'inizio di ogni
  transazione. Una sessione senza tenant non vede righe.
- Le sole tabelle senza policy per tenant sono quelle di `tenancy` (tenant, utenti, membership),
  usate da `ResolveTenantUseCase` prima che il tenant sia noto.
- Unica lettura senza tenant fuori da `tenancy`: `telegram_link_codes` per il digest dichiarato in
  `app.link_code_digest`, sola lettura di quella riga (ADR 0035).
- Un'entità di un altro tenant passata all'adapter solleva `CrossTenantAccessError`.

## Test

Integrazione su PostgreSQL vero in container: migrazioni applicate da zero, isolamento RLS verificato
con due tenant.
