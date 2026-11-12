---
paths:
  - "src/autotrading/*/flows/**"
  - "tests/**/flows/**"
  - "specs/E1-flussi-autonomi/F1.1-flussi-di-trading/**"
  - "specs/E1-flussi-autonomi/F1.5-rischio-ed-esecuzione/**"
  - "specs/E1-flussi-autonomi/F1.6-capitale-dei-flussi/**"
  - "specs/E1-flussi-autonomi/F1.7-registrazione-e-consultazione/R1.7.2-*"
---

# Contesto flows

Il flusso di trading: che cosa opera, con quali regole e con quale capitale.

## Glossario

- **Flow**: agente che opera in autonomia su un conto, con nome, asset, intervallo di ciclo, modello IA,
  fonti, istruzioni, limiti di rischio e capitale allocato (R1.1.1).
- **Configuration version**: configurazione immutabile e numerata in ordine crescente; ogni modifica
  accettata ne crea una nuova (R1.1.3). Un ciclo usa la versione letta al suo inizio.
- **Flow status**: `stopped` (fermo), `active` (attivo), `paused` (in pausa, con il motivo se automatica),
  `archived` (archiviato, definitivo) (R1.1.4-R1.1.6).
- **Allocated capital**: quota del saldo del conto assegnata al flusso. **Free capital** del conto: saldo
  letto dall'exchange meno i capitali allocati ai flussi non archiviati (R1.1.7).
- **Available liquidity** del flusso: capitale allocato, più PnL realizzato delle sue esecuzioni, meno le
  sue commissioni, meno il margine delle sue posizioni aperte (R1.6.1).
- **Risk limits**: leva massima (obbligatoria) ed esposizione per operazione sul margine e sul valore
  (almeno una); opzione "porta al minimo" (R1.5.1-R1.5.4).
- **Risk outcome** di una decisione: approvata, ridotta, bloccata (R1.5.x); scartata è di `agent` (R1.4.5).
- **Unattributable item**: posizione, esecuzione o variazione di saldo del conto che nessun flusso spiega
  (R1.6.2).
- **Closed position**: posizione di un flusso chiusa, con risultato e motivo di chiusura (R1.7.2).

## Regole

- **Conflitto sugli asset**: due flussi non archiviati dello stesso conto non hanno asset in comune
  (R1.1.2). È ciò che rende una posizione attribuibile al flusso per asset.
- **Nessuna liquidità propria**: lo stato del flusso si ricava da ciò che l'exchange mostra. Le posizioni
  si attribuiscono per asset, le esecuzioni per identificativo dell'ordine (`ClientOrderId`, contesto
  `orders`). La piattaforma non tocca ciò che non attribuisce.
- Stati e transizioni sono regole del domain: avvia da fermo, pausa da attivo, riprendi da in pausa,
  archivia solo da fermo; un flusso archiviato non si avvia e non si modifica (ADR 0036).
- Il conto di un flusso non cambia mai. Un asset con posizione aperta non si toglie dalla configurazione.
- Lo stop chiude sempre le posizioni del flusso (decisione del proprietario: senza stop loss sull'exchange
  una posizione lasciata aperta non è protetta), dopo il ciclo in corso.
- Ordine del controllo del rischio: leva, poi esposizione, poi coerenza con lo stato, poi importo minimo.
- Gli ordini passano dal contesto `orders` (apertura, chiusura, esito reale); `flows` non parla con
  l'exchange per inviare ordini.

## Porte del contesto

- `FlowRepositoryPort`: flussi del tenant con la versione di configurazione in vigore; nome unico tra i non
  archiviati (ADR 0031); legge un flusso per id e ogni sua versione, salva lo stato e le versioni nuove
  senza toccare le precedenti (ADR 0036).
- `FlowAccountPort`: exchange e saldo del conto letti ora, dal contesto `accounts` attraverso il `worker`.
- `ModelSettingsPort`, `SourceSettingsPort`: modello e fonti con i parametri risolti, dai contesti `agent` e
  `sources`; un rifiuto arriva come `InvalidFlowSettingError` con il motivo del contesto che lo dà.
- `MarketsPort`: asset negoziabili ora sull'exchange, per nome dell'exchange.
- `AccountActivityPort`: ciò che l'exchange mostra del conto ora (posizioni con margine, esecuzioni con `cloid`,
  movimenti del saldo), letto dal `worker` e chiesto dall'API via HTTP interno (ADR 0044).
- `PlatformOrdersPort`: i `cloid` degli ordini registrati sul conto, con il flusso che li ha inviati (contesto `orders`).
- `ReconciliationRepositoryPort`: ultima lettura di ogni conto e non attribuibili registrati una volta (ADR 0045).
- `ClosedPositionsPort`: storico delle posizioni chiuse dei flussi (R1.7.2).
- I bridge verso gli altri contesti vivono solo in `bootstrap.py`; `flows` fornisce ad `agent` i flussi che
  usano una chiave (`ProviderKeyUsageFromFlows`).

Repository delle variazioni di capitale e invio degli ordini attraverso `orders` nascono con i requisiti che li
usano.
