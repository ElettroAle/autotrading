# ADR scadenza-delle-chiavi-letta-o-indicata — Scadenza di ogni chiave, letta dall'adapter o indicata dall'utente

- Stato: proposta (19 novembre 2026)
- Requisiti: US 383 R6.2.2, Task 384
- Collegate: ADR 0007 (credenziali leggibili solo dal worker); `.claude/rules/context-accounts.md`,
  `.claude/rules/context-agent.md`, `.claude/rules/tech-hyperliquid.md`
- Verifica: prova

## Contesto e problema

Le chiavi della piattaforma sono le credenziali dei conti (`accounts`, `Account` con `SealedCredentials`) e le chiavi
dei fornitori IA (`agent`, `RegisteredProviderKey`); con F4.1 arriveranno le credenziali degli adapter delle fonti.
Nessuna ha una data di scadenza. R6.2.2 la vuole letta dall'adapter quando il fornitore la espone (validità dell'API
wallet di Hyperliquid) e aggiornata a ogni verifica, altrimenti indicata dall'utente; senza data «scadenza sconosciuta».

## Fattori decisionali

- R6.2.2 (proprietario) e la decisione del 15/11/2026: data letta quando il fornitore la espone, altrimenti a mano.
- Ogni contesto possiede le sue chiavi: nessun tipo condiviso tra contesti oltre `tenancy`.
- Un adapter dichiara ciò che sa fare (come `credential_fields`); il domain non nomina fornitori.

## Decisione

- Domain, in ciascun contesto che ha chiavi (`accounts`, `agent`; poi `sources` con R4.1.2): la chiave porta
  `expiry: KeyExpiry | None`, value object del contesto con la data (`date`, UTC) e l'origine (`read` dall'adapter,
  `entered` dall'utente). Nessuna data = scadenza sconosciuta.
- Adapter: `ExchangePort.reads_credential_expiry() -> bool` e `ExchangePort.credential_expiry(credentials) -> date |
  None` (Hyperliquid: info `extraAgents` del conto principale, campo `validUntil` dell'API wallet delle credenziali;
  `None` se il fornitore non la espone). Per i fornitori IA la stessa dichiarazione nell'adapter del catalogo
  (`False` per tutti oggi).
- La verifica delle credenziali che il worker già fa (registrazione, sostituzione, verifica del conto) legge la data e
  la salva con origine `read`.
- Indicazione a mano: `SetAccountKeyExpiryUseCase` e `SetProviderKeyExpiryUseCase` (data o nessuna), ammessi solo
  quando l'adapter non legge la scadenza (altrimenti `KeyExpiryReadByAdapterError`, 409); la data si può dare anche
  nei moduli di registrazione e di sostituzione. Sostituire la chiave toglie la data indicata prima.
- API: ogni chiave e ogni conto espongono `expiry` (data, origine), `expiry_editable` e `expiry_status` calcolato nel
  domain alla data di oggi: `unknown`, `valid`, `expiring` (entro 30 giorni), `expired`, con `days_left`.
- SQLAlchemy: colonne `expires_on DATE NULL` e `expiry_source TEXT NULL` (CHECK) su conti e chiavi dei fornitori;
  migrazione dopo l'ultima.

## Alternative scartate

- Un registro unico delle chiavi in un contesto nuovo: un contesto nuovo nasce solo con decisione del proprietario.
- Data a mano sempre ammessa: contraddirebbe la data letta a ogni verifica.

## Conseguenze

- R4.1.2 aggiunge la stessa scadenza alle credenziali degli adapter delle fonti.
