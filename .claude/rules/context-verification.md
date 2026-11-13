---
paths:
  - "src/autotrading/*/verification/**"
  - "tests/**/verification/**"
  - "specs/E0-esecuzione-verificata/F0.4-procedura-di-verifica/**"
---

# Contesto verification

## Glossario

- **Verification run**: esecuzione della procedura su un conto del tenant: apertura long BTC leva 2
  del valore scelto dall'utente (o del minimo dell'exchange del conto), lettura, chiusura, rilettura
  (R0.4.1). Posseduta da un tenant (`TenantOwned`).
- **Step outcome**: esito di ciascun passo, registrato anche quando il passo fallisce.

## Regole

- Orchestra `accounts` e `orders` solo tramite porte proprie (es. `AccountStatePort`,
  `OrderExecutionPort`), collegate in `bootstrap.py` ai casi d'uso di quei contesti. Nessun import
  dei loro interni.
- Un passo fallito interrompe la procedura; gli esiti dei passi già eseguiti restano registrati.
- La procedura non parte su BTC se un flusso attivo o in pausa del conto ha BTC tra i suoi asset
  (`AssetOfFlowError`, 409): le sue esecuzioni cambierebbero la posizione che il flusso si aspetta e lo
  metterebbero in pausa. I suoi ordini (origine "procedura di verifica") non appartengono a nessun flusso:
  nel registro sono non attribuiti (ADR 0075).
- Il minimo e le regole dell'ordine arrivano dall'exchange attraverso `OrderExecutionPort`, mai
  cablati nel domain. Mentre la procedura è in corso su un asset di un conto nessun flusso del conto
  su quell'asset si avvia o riprende: lo stato è un advisory lock di PostgreSQL condiviso da API e
  worker (ADR 0079).
