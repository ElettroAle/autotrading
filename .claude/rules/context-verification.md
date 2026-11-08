---
paths:
  - "src/autotrading/*/verification/**"
  - "tests/**/verification/**"
  - "specs/E0-esecuzione-verificata/F0.4-procedura-di-verifica/**"
---

# Contesto verification

## Glossario

- **Verification run**: esecuzione della procedura su un conto del tenant: apertura long BTC leva 2
  per 12 USDC, lettura, chiusura, rilettura (R0.4.1). Posseduta da un tenant (`TenantOwned`).
- **Step outcome**: esito di ciascun passo, registrato anche quando il passo fallisce.

## Regole

- Orchestra `accounts` e `orders` solo tramite porte proprie (es. `AccountStatePort`,
  `OrderExecutionPort`), collegate in `bootstrap.py` ai casi d'uso di quei contesti. Nessun import
  dei loro interni.
- Un passo fallito interrompe la procedura; gli esiti dei passi già eseguiti restano registrati.
