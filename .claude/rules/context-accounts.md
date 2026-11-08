---
paths:
  - "src/autotrading/*/accounts/**"
  - "tests/**/accounts/**"
  - "specs/E0-esecuzione-verificata/F0.2-conti-di-trading/**"
---

# Contesto accounts

## Glossario

- **Account** (conto di trading): collegamento a un conto su un exchange, posseduto da un tenant
  (`TenantOwned`). Nome univoco nel tenant.
- **Credentials**: chiavi generate dall'utente sull'exchange. Il database conserva solo il
  riferimento; il contenuto sta nel vault (R0.2.3).
- **Account state**: saldo, margine disponibile, posizioni aperte, letti dall'exchange.

## Regole

- Le credenziali non compaiono mai in risposte, log, errori o eccezioni: il tipo che le contiene ha
  un `__repr__` che le maschera.
- Alla registrazione e alla sostituzione le credenziali si controllano leggendo il saldo prima di
  salvarle (R0.2.1, R0.2.4). Nessun controllo sui permessi di prelievo.
- Il conto non ha un attributo test/reale: la rete di test si sceglie per configurazione
  dell'installazione `dev`.
- La rimozione con posizioni aperte richiede conferma esplicita (R0.2.5).

## Porte del contesto

`ExchangePort` (lettura di saldo e stato), `SecretVaultPort` (credenziali), `AccountRepositoryPort`.
