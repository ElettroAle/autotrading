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
  di arrotondamento stanno nel domain. La quantità si arrotonda per difetto, ma per eccesso di un passo quando un
  valore che rispetta il minimo dell'exchange scenderebbe sotto di esso (ADR 0066).
- Nessun nuovo tentativo automatico di un ordine fallito (R0.3.3).
- Ogni posizione si apre con margine isolato (`MarginMode.per_position()`, ADR 0095): il caso d'uso lo passa
  alla porta con la leva.

## Porte del contesto

`ExchangePort` (ordini, ricerca per identificativo, metadati degli asset), `OrderRepositoryPort`.
Gli ordini approvati di un ciclo arrivano da `flows` come `CycleOrdersPort` con elementi `ApprovedOrderPort`;
`ExecuteCycleOrdersUseCase` li invia e li segue (ADR 0098).
