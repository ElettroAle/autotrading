---
paths:
  - "src/autotrading/*/orders/**"
  - "tests/**/orders/**"
  - "specs/E0-esecuzione-verificata/F0.3-esecuzione-degli-ordini/**"
---

# Contesto orders

## Glossario

- **Order**: richiesta di apertura o chiusura inviata all'exchange, con identificativo assegnato
  dalla piattaforma (`ClientOrderId`, il `cloid` dell'exchange) che la collega a chi l'ha generata.
- **Position**: esposizione aperta su un asset, `long` o `short`, con leva.
- **Slippage**: scostamento massimo di prezzo accettato; configurabile, predefinito 5%.
- **Execution outcome**: esito reale letto dall'exchange (prezzo, dimensione, commissioni), mai quello
  atteso (R0.3.4).

## Regole

- L'apertura non è un comando dell'utente: la usano la procedura di verifica e, in seguito, i flussi.
  L'utente può solo chiudere manualmente (R0.3.2).
- Leva massima e passo della dimensione dell'asset vengono dall'exchange; le regole di controllo e
  di arrotondamento stanno nel domain.
- Nessun nuovo tentativo automatico di un ordine fallito (R0.3.3).

## Porte del contesto

`ExchangePort` (ordini, ricerca per identificativo, metadati degli asset), `OrderRepositoryPort`.
