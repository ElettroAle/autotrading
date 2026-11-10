# ADR 0022 — Apertura delle posizioni ed esito reale degli ordini nel contesto orders

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.3.1, R0.3.3, R0.3.4

## Contesto

R0.3.1 chiede di aprire una posizione long o short con leva e valore indicati. L'ordine è a mercato con
uno scostamento massimo di prezzo: configurabile, 5% se non configurato. Ogni ordine porta un
identificativo della piattaforma. La leva oltre il massimo dell'exchange non parte. La dimensione si
arrotonda al passo dell'asset.

R0.3.3 chiede che un rifiuto sia riportato con un motivo leggibile e con il messaggio originale, e che sia
registrato. Nessun nuovo tentativo. Se l'exchange non risponde all'invio, si cerca l'ordine per
identificativo; se non risulta, l'esito è "esito sconosciuto".

R0.3.4 chiede di registrare ciò che l'exchange ha eseguito davvero: dimensione, prezzo medio, commissione
e istante. Un'esecuzione parziale si registra come "eseguito in parte". Ogni ordine registra la sua origine.

Le regole del repository vietano a un contesto del domain di importare un altro contesto, tranne
`tenancy`. Le credenziali salvate le apre solo il `worker` (ADR 0007, ADR 0021).

## Decisione

- **Contesto `orders` autonomo.**
  - Il domain non importa `accounts`. Il conto si nomina con il suo UUID.
  - Le credenziali arrivano come `TradingAccess`: exchange, indirizzo e chiave, con `repr` oscurato.
  - La porta `TradingAccessPort.access(account_id)` le fornisce. In `bootstrap` la collega al
    contesto `accounts` (conto sotto RLS e opener del `worker`) il primo requisito che la espone, R0.3.2.
- **Domain**:
  - `ClientOrderId`: UUID di 128 bit, il `cloid` di Hyperliquid.
  - `Slippage`: frazione tra 0 e 1, predefinita 5%.
  - `Market`: coin, leva massima, decimali della dimensione e prezzo medio. Fornisce due regole:
    - `require_leverage`: oltre il massimo solleva `LeverageAboveMaximumError` con il massimo dell'asset;
    - `size_for(valore)`: valore diviso prezzo medio, arrotondato per difetto al passo, mai oltre il
      valore chiesto. Una dimensione che si arrotonda a zero è un errore.
  - `MarketOrder`: ciò che si invia.
  - `Order`: ciò che si registra. Contiene richiesta, origine, utente facoltativo e stato, che è
    "eseguito", "eseguito in parte", "rifiutato" o "esito sconosciuto". Con l'esecuzione registra la
    dimensione, il prezzo medio, la commissione, il risultato realizzato e l'istante letti dall'exchange.
  - `Rejection.of(messaggio)` classifica il messaggio dell'exchange:
    - "minimum value": importo sotto il minimo;
    - "insufficient margin": margine insufficiente;
    - "unknown asset": asset non disponibile;
    - "could not immediately match": prezzo oltre lo scostamento massimo, cioè l'IOC non trova prezzi
      entro il limite;
    - altrimenti: rifiuto dell'exchange.
    Il messaggio originale resta sempre nell'esito.
- **Caso d'uso `OpenPositionUseCase`** (contesto `orders`, eseguito nel `worker`):
  1. accesso al conto;
  2. scelta dell'exchange;
  3. lettura del mercato e controllo della leva: oltre il massimo, nessun ordine e nessuna registrazione;
  4. dimensione arrotondata e nuovo `ClientOrderId`;
  5. impostazione della leva e invio;
  6. registrazione dell'esito, che è anche il valore restituito.
  Un rifiuto è un esito, non un'eccezione. Su `OrderNotAcknowledgedError` il caso d'uso cerca l'ordine
  per identificativo, una volta: se lo trova registra l'esecuzione trovata, altrimenti "esito sconosciuto".
  Lo scostamento arriva dal costruttore; la sua lettura dalla configurazione arriva con il collegamento
  in `bootstrap`.
- **Porta `ExchangePort` di `orders`**: `market`, `set_leverage`, `place_market_order` e `find_order`.
  L'adapter `HyperliquidOrderExchangeAdapter` usa:
  - `meta` per leva massima e decimali, `all_mids` per il prezzo medio;
  - `update_leverage` in cross;
  - `market_open` e `market_close` con `cloid` e scostamento;
  - `query_order_by_cloid` per la ricerca.
  L'esecuzione si calcola dai fill dell'ordine (`user_fills`, per `oid`): somma delle dimensioni, prezzo
  medio pesato, somma di commissioni e risultato realizzato, istante dell'ultimo fill. Un ordine
  eseguito di cui non si vedono ancora i fill è un ordine non confermato e passa dalla ricerca. Un
  timeout di rete all'invio è `OrderNotAcknowledgedError`.
- **Registrazione**: tabella `orders` con RLS per tenant (migrazione 0004), chiave primaria il
  `ClientOrderId`, importi `NUMERIC`. `SqlAlchemyOrderRepositoryAdapter.add`.

## Alternative scartate

- **`orders` che importa `Credentials` e `AccountId` di `accounts`**: contro la regola sui contesti del
  domain. Il prezzo è un tipo di accesso duplicato, piccolo e senza logica.
- **Classificazione dei messaggi nell'adapter**: gli scenari, che girano su un exchange finto, non la
  proverebbero.
- **Rifiuto come eccezione**: l'esito rifiutato va registrato e restituito, e il chiamante (la procedura
  di verifica) lo riporta come passo fallito.
- **Dimensione arrotondata al più vicino**: potrebbe superare il valore chiesto e il margine previsto.
- **Commissione stimata dal listino**: contro R0.3.4, che vuole quella letta.

## Conseguenze

- Le porte di `orders` non hanno ancora rotte: l'apertura la useranno la procedura di verifica (R0.4.1)
  e i flussi; la chiusura manuale (R0.3.2) collega `TradingAccessPort` e lo scostamento configurato.
- Un asset sconosciuto all'SDK fallisce alla lettura del mercato, prima che esista un ordine da registrare.
- `docs/architecture.md` prevede anche una tabella `fills`. Per E0 l'esecuzione aggregata sta nella riga
  dell'ordine; i singoli fill arriveranno con la contabilità dei flussi, se servono.
- La chiave esterna composta (conto, tenant) impedisce di registrare un ordine su un conto di un altro
  tenant, cosa che la sola RLS non impedisce perché le chiavi esterne si controllano senza di essa.
