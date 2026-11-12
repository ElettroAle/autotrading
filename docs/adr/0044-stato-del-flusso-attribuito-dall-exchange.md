# ADR 0044 — Stato del flusso attribuito da ciò che l'exchange mostra

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.1 (Task T1.6.1.1)

## Contesto

Lo stato di un flusso (posizioni, liquidità disponibile, valore complessivo, rendimento) va ricavato da ciò che
l'exchange mostra, perché la piattaforma non tiene una liquidità propria. L'exchange conosce solo i totali del
conto: la piattaforma deve ripartirli tra i flussi. La rule di `flows` fissa i criteri: le posizioni si
attribuiscono per asset (due flussi non archiviati dello stesso conto non hanno asset in comune, R1.1.2), le
esecuzioni per identificativo dell'ordine (`ClientOrderId`, il `cloid` di Hyperliquid). Le credenziali le apre solo
il `worker` (ADR 0007); l'API raggiunge il worker via HTTP interno (ADR 0021).

## Decisione

- **Domain** (`flows`): `AccountActivity` è la lettura del conto (valuta, saldo, margine disponibile, posizioni con
  margine e PnL non realizzato, esecuzioni con il `cloid` se c'è, movimenti del saldo). `FlowState.attributed` tiene
  le posizioni sugli asset del flusso e le esecuzioni dei suoi ordini, e ne ricava:
  - liquidità disponibile = capitale allocato + PnL realizzato − commissioni − margine delle posizioni;
  - valore complessivo = liquidità + margine + PnL non realizzato;
  - rendimento dall'avvio = (valore − capitale allocato) / capitale allocato × 100.
  Il capitale di riferimento è quello allocato in vigore: una variazione (R1.1.7) sposta il riferimento da quel
  momento, come chiede il requisito.
- **Caso d'uso** `ReadFlowStateUseCase` nell'API, con tre porte: `FlowRepositoryPort`, `AccountActivityPort`
  (attività del conto ora) e `PlatformOrdersPort` (i `cloid` degli ordini registrati sul conto, con il flusso che
  li ha inviati o nessuno).
- **Lettura dall'exchange**: `HyperliquidAccountActivityAdapter` legge `clearinghouseState` (posizioni con
  `marginUsed`), le esecuzioni con `userFillsByTime` a pagine da 2000 dall'inizio, e i movimenti con
  `userNonFundingLedgerUpdates`. Sono informazioni pubbliche dell'indirizzo: non si firma nulla.
- **Percorso**: l'API chiede al worker `GET /tenants/{t}/accounts/{a}/activity` (`HttpxAccountActivityAdapter`);
  il worker trova il conto del tenant sotto RLS e lo apre solo per conoscerne l'indirizzo
  (`AccountActivityFromAccounts` in `bootstrap.py`). L'API espone `GET /flows/{id}/state`; un flusso di un altro
  tenant non si trova (404).
- **Ordini della piattaforma**: `SqlAlchemyPlatformOrdersAdapter` legge identificativo e flusso dalla tabella `orders`
  (ADR 0050). Gli ordini della procedura di verifica e dei comandi manuali non hanno flusso.

## Alternative scartate

- **Liquidità tenuta dalla piattaforma** (registro interno di depositi e PnL): il requisito vieta una liquidità
  propria; si allontanerebbe da ciò che l'exchange mostra a ogni intervento esterno.
- **Esecuzioni ricostruite dagli ordini registrati**: un'esecuzione fuori dalla piattaforma non comparirebbe, e
  R1.6.2 la deve vedere.
- **`userFills`** (le ultime 2000): un flusso attivo da settimane le supera. Con `userFillsByTime` a pagine si
  arriva al limite dell'exchange, le 10000 esecuzioni più recenti del conto.
- **Lettura dall'API senza worker**: l'indirizzo del conto è dentro le credenziali cifrate, che apre solo il worker.

## Conseguenze

- Oltre le 10000 esecuzioni più recenti del conto l'exchange non restituisce le più vecchie: il PnL realizzato di
  un flusso molto attivo da molto tempo ne perderebbe una parte. Se servirà, le esecuzioni lette si potranno
  conservare nel database.
- Il ciclo (F1.2) legge lo stato del flusso con lo stesso caso d'uso per il controllo del rischio (ADR 0040).
