# ADR 0040 — Controllo del rischio come regola del domain di flows

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.5.1, R1.5.2, R1.5.3, R1.5.4 (Task T1.5.1.1, T1.5.2.1, T1.5.3.1, T1.5.4.1)

## Contesto

Le decisioni conformi dell'agente passano dal controllo del rischio prima di diventare ordini: leva massima del
flusso e dell'exchange (R1.5.2), esposizione per operazione sul margine e sul valore (R1.5.1), coerenza con lo
stato del flusso (R1.5.3), importo minimo dell'exchange con l'opzione "porta al minimo" (R1.5.4). La rule di
`flows` fissa l'ordine: leva, esposizione, coerenza, minimo. Le decisioni nascono nel contesto `agent`, che
`flows` non può importare (ADR 0026). Il ciclo (F1.2) che collega agente, rischio ed esecuzione non esiste ancora.

## Decisione

- **Tipi propri di `flows`** per l'intenzione: `OpenIntent` (asset, lato, quota del capitale come margine, leva),
  `CloseIntent`, `HoldIntent`. La traduzione dalla decisione dell'agente avviene nel ciclo, in `bootstrap.py`.
- **Esiti**: `ApprovedOpening` (valore e leva; il margine ne deriva; con le rettifiche registrate: tipo, da, a,
  motivo), `ApprovedClose`, `BlockedDecision` con motivo, `HeldPosition`. L'apertura approvata porta il **valore**,
  perché è il valore che dimensiona l'ordine: un limite sul valore non diventa un valore con decimali periodici.
- **Regola** `RiskCheck` nel domain, una decisione alla volta:
  1. leva oltre il massimo del flusso, poi oltre il massimo dell'exchange per l'asset: ridotta mantenendo il
     margine, una rettifica per ciascun limite superato;
  2. esposizione: margine = quota × capitale allocato; il limite sul margine ammette un valore di
     capitale × % × leva, quello sul valore di capitale × %; vale il più restrittivo, e si registra la rettifica
     del limite che vincola (margine o valore, come negli scenari);
  3. coerenza: posizione già aperta sull'asset, chiusura di una posizione inesistente, margine oltre la liquidità
     disponibile dopo le riduzioni: bloccata;
  4. minimo dell'exchange: bloccata, oppure con "porta al minimo" il valore sale al minimo se il minimo rispetta il
     limite di esposizione e la liquidità.
  - I numeri dei motivi si scrivono come li legge l'utente: senza zeri finali, con la virgola ("0,5%").
- **Caso d'uso** `CheckRiskUseCase` con la porta `ExchangeLimitsPort.limits(asset)` (leva massima e valore minimo,
  `None` se l'exchange non tratta l'asset: apertura bloccata "asset non negoziabile sull'exchange"). Chiusure e
  mantenimenti non chiedono i limiti all'exchange.
- **Adapter**: `HyperliquidMarketsAdapter.limits` legge `maxLeverage` dai metadati pubblici (`meta`); il valore
  minimo è 10 USDC, il minimo che l'exchange dichiara ("Order must have minimum value of $10").
- **Politica** `RiskPolicy(limiti di rischio, porta al minimo)`: l'opzione "porta al minimo" entra nella
  configurazione del flusso con il ciclo, per non sovrapporsi alla modifica versionata della configurazione
  (R1.1.3) in sviluppo in parallelo.

## Alternative scartate

- **Importare la decisione di `agent` in `flows`**: viola l'indipendenza dei contesti (ADR 0026).
- **Scartare un'apertura oltre un limite**: il requisito la vuole ridotta ed eseguita.
- **Esito con il margine come grandezza primaria**: un limite sul valore con leva 3 darebbe 99,99999 invece di 100.
- **Minimo dell'exchange letto per asset da un'API**: Hyperliquid non lo espone nei metadati; è una regola unica
  dell'exchange, documentata.

## Conseguenze

- Il ciclo (F1.2) traduce le decisioni in intenzioni, legge lo stato del flusso all'inizio (capitale allocato,
  liquidità disponibile, asset con posizione aperta: F1.6), chiama il caso d'uso, registra rettifiche e blocchi
  ed esegue gli approvati (R1.5.5).
- L'opzione "porta al minimo" va aggiunta alla configurazione del flusso e alla sua API.
