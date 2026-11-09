---
paths:
  - "src/autotrading/domain/tenancy/**"
  - "src/autotrading/application/tenancy/**"
  - "src/autotrading/bootstrap.py"
  - "src/autotrading/adapters/outbound/sqlalchemy/**"
  - "migrations/**"
  - "tests/**/tenancy/**"
  - "specs/E0-esecuzione-verificata/F0.1-accesso-alla-piattaforma/**"
---

# Contesto tenancy

## Glossario

- **User**: persona censita in Entra con il ruolo `Utente`. `UserId` = `oid` del token, stabile.
  Il nome visualizzato non identifica mai un utente.
- **Tenant**: contenitore isolato di tutto ciò che appartiene a un utente (conti, credenziali,
  flussi, risultati, impostazioni). `TenantId` è un identificativo proprio (UUID), distinto da `UserId`.
- **Membership**: legame tra un `UserId` e un `TenantId`. In E0 il database impone un tenant per
  utente e un utente per tenant, il proprietario; il vincolo si allenta in futuro senza migrare i dati.
- `tenant_id` dice **a chi appartiene** un dato; `user_id` dice **chi ha fatto** un'azione (audit).

## Regole

- `domain/tenancy` è l'unico contesto importabile da tutti gli altri contesti.
- **`TenantOwned`**: classe base astratta in `domain/tenancy`. Ogni entità che appartiene a un tenant
  la estende e porta `tenant_id: TenantId`. Le uniche entità che non la estendono sono `Tenant`,
  `User` e `Membership`.
- **Porte legate al tenant.** I repository dei dati posseduti si costruiscono con il
  tenant della richiesta (`bootstrap.for_tenant`). I loro metodi non ricevono mai `tenant_id`.
- Un adapter legato al tenant che riceve un'entità di un altro tenant solleva `CrossTenantAccessError`.
- Un elemento di un altro tenant è **non trovato**: stesso errore e stessa risposta di un elemento
  inesistente, senza indizi sulla sua esistenza (R0.1.3).
- `ResolveTenantUseCase` trova il tenant dell'utente dall'`oid` o lo crea al primo accesso (R0.1.2).
  È l'unico caso d'uso che lavora prima che il tenant della richiesta sia noto.
- **Row level security**: vive solo nell'adapter SQLAlchemy (vedi `tech-sqlalchemy.md`). Domain e
  application non ne sanno nulla.

## Test obbligatori

- Unit test: ogni entità persistita da un repository estende `TenantOwned`.
- Integrazione: con la sessione legata al tenant A nessuna lettura restituisce righe del tenant B,
  anche con una query scritta senza filtro.
